# ruff: noqa: E402
"""MilkyWay M17 — Policy Student Distillation Pipeline.

Distills knowledge from large ResNet teacher into compact ~1.3M parameter
ChessPolicyStudent designed for single-core CPU competition runtime.

Loss:
  0.7 * Soft Distillation Loss (KL divergence from teacher logits)
  + 0.3 * Hard Target Cross-Entropy (from ground truth / Stockfish moves)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F  # noqa: N812
from torch.amp.autocast_mode import autocast
from torch.amp.grad_scaler import GradScaler

from training.data.dataset import ShardedChessDataset, create_dataloader
from training.metrics.evaluator import evaluate_failure_positions
from training.models.student import ChessPolicyStudent
from training.models.teacher import create_teacher
from training.scripts.train_teacher import get_cosine_schedule_with_warmup, get_git_commit


def distill_student(
    teacher_checkpoint: Path,
    dataset_dir: Path,
    teacher_arch: str = "teacher_b",
    batch_size: int = 512,
    epochs: int = 5,
    lr: float = 1e-3,
    alpha_kd: float = 0.7,
    temperature: float = 2.0,
    checkpoint_dir: Path = Path("training/checkpoints/student"),
    device_str: str = "cuda" if torch.cuda.is_available() else "cpu",
    num_workers: int = 0,
    seed: int = 42,
) -> Path:
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device(device_str)

    # 1. Load teacher
    print(f"Loading teacher from {teacher_checkpoint} ({teacher_arch})...")
    teacher = create_teacher(teacher_arch).to(device)
    t_ckpt = torch.load(teacher_checkpoint, map_location=device)
    teacher.load_state_dict(t_ckpt["model_state_dict"])
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad = False

    # 2. Instantiate student
    student = ChessPolicyStudent().to(device)
    print(f"Initialized student: {student.count_parameters():,} parameters")

    # 3. Load data
    train_shards = sorted(list((dataset_dir / "train").glob("*.npz")))
    val_shards = sorted(list((dataset_dir / "val").glob("*.npz")))
    train_dataset = ShardedChessDataset(train_shards, preload=True)
    val_dataset = ShardedChessDataset(val_shards, preload=True) if val_shards else None

    train_loader = create_dataloader(
        train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers
    )
    val_loader = (
        create_dataloader(
            val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
        )
        if val_dataset
        else None
    )

    optimizer = torch.optim.AdamW(student.parameters(), lr=lr, weight_decay=1e-4)
    scaler = GradScaler("cuda", enabled=(device.type == "cuda"))
    total_steps = len(train_loader) * epochs
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, num_warmup_steps=50, num_training_steps=total_steps
    )

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    best_top1 = 0.0
    global_step = 0

    print("=== Starting Student Distillation ===")
    print(f"Total steps: {total_steps}, Epochs: {epochs}, Batch size: {batch_size}")

    dev_type = "cuda" if device.type == "cuda" else "cpu"
    amp_enabled = device.type == "cuda"

    for epoch in range(epochs):
        student.train()
        for batch in train_loader:
            global_step += 1
            optimizer.zero_grad(set_to_none=True)

            boards = batch["board"].to(device, non_blocking=True)
            policy_idx = batch["policy_idx"].to(device)
            policy_mask = batch["policy_mask"].to(device)

            with torch.no_grad(), autocast(
                device_type=dev_type, dtype=torch.float16, enabled=amp_enabled
            ):
                t_logits = teacher(boards)[0]

            with autocast(device_type=dev_type, dtype=torch.float16, enabled=amp_enabled):
                s_logits = student(boards)

                # KD Soft Loss
                t_probs = F.softmax(t_logits / temperature, dim=-1)
                s_log_probs = F.log_softmax(s_logits / temperature, dim=-1)
                kd_loss = -(t_probs * s_log_probs).sum(dim=-1).mean() * (temperature ** 2)

                # Hard Cross-Entropy Loss
                hard_ce = F.cross_entropy(s_logits, policy_idx, reduction="none")
                hard_loss = (hard_ce * policy_mask).sum() / (policy_mask.sum() + 1e-8)

                loss = alpha_kd * kd_loss + (1.0 - alpha_kd) * hard_loss

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            if global_step % 50 == 0 or global_step == 1:
                loss_str = (
                    f"Epoch {epoch+1}/{epochs} | Step {global_step}/{total_steps} | "
                    f"Loss: {loss.item():.4f} (KD: {kd_loss.item():.3f}, "
                    f"Hard: {hard_loss.item():.3f}) | LR: {scheduler.get_last_lr()[0]:.2e}"
                )
                print(loss_str)

        # Validation
        if val_loader:
            student.eval()
            val_correct_top1 = 0
            val_correct_top3 = 0
            val_teacher_agreed: float = 0.0
            val_total = 0

            with torch.no_grad():
                for batch in val_loader:
                    boards = batch["board"].to(device, non_blocking=True)
                    p_idx = batch["policy_idx"].to(device)
                    p_mask = batch["policy_mask"].to(device)

                    with autocast(device_type=dev_type, dtype=torch.float16, enabled=amp_enabled):
                        s_logits = student(boards)
                        t_logits = teacher(boards)[0]

                    valid = p_mask > 0.5
                    if valid.any():
                        s_top3 = torch.topk(s_logits[valid], k=3, dim=-1).indices
                        targets = p_idx[valid].unsqueeze(-1)
                        val_correct_top1 += (s_top3[:, :1] == targets).sum().item()
                        val_correct_top3 += (s_top3 == targets).any(dim=-1).sum().item()

                        t_top1 = torch.argmax(t_logits[valid], dim=-1)
                        s_top1 = s_top3[:, 0]
                        val_teacher_agreed += float((s_top1 == t_top1).sum().item())
                        val_total += valid.sum().item()

            top1_acc = val_correct_top1 / max(1, val_total)
            top3_acc = val_correct_top3 / max(1, val_total)
            t_agreement = val_teacher_agreed / max(1, val_total)

            print(
                f"--- Epoch {epoch+1} Student Val --- "
                f"Top-1: {top1_acc:.3f} | Top-3: {top3_acc:.3f} | "
                f"Teacher Agreement: {t_agreement:.3f}"
            )

            # Failure benchmark
            failures = evaluate_failure_positions(student, device=str(device))
            for f_item in failures:
                blunder_info = (
                    f"Blunder {f_item['blunder_move']} rank: "
                    f"{f_item['blunder_rank']}/{f_item['total_legal_moves']}"
                )
                good_info = f"Best good {f_item['best_good_move']} rank: {f_item['best_good_rank']}"
                pref = f_item['good_preferred_over_blunder']
                print(
                    f"Student Failure [{f_item['name']}]: {blunder_info} | "
                    f"{good_info} | Safe retreat preferred: {pref}"
                )

            if top1_acc > best_top1:
                best_top1 = top1_acc
                best_student_path = checkpoint_dir / "best_student.pt"
                torch.save(
                    {
                        "step": global_step,
                        "arch": "chess_policy_student_64x4",
                        "model_state_dict": student.state_dict(),
                        "top1_acc": top1_acc,
                        "teacher_agreement": t_agreement,
                        "git_commit": get_git_commit(),
                    },
                    best_student_path,
                )

    latest_path = checkpoint_dir / "latest_student.pt"
    torch.save(
        {
            "step": global_step,
            "arch": "chess_policy_student_64x4",
            "model_state_dict": student.state_dict(),
            "git_commit": get_git_commit(),
        },
        latest_path,
    )
    print(f"Distillation complete. Best student saved to {checkpoint_dir / 'best_student.pt'}")
    return checkpoint_dir / "best_student.pt"


def main() -> None:
    parser = argparse.ArgumentParser(description="MilkyWay student distillation.")
    parser.add_argument(
        "--teacher-checkpoint",
        type=Path,
        default=Path("training/checkpoints/teacher/best_policy.pt"),
    )
    parser.add_argument("--dataset-dir", type=Path, default=Path("training/datasets/smoke_50k"))
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    distill_student(
        teacher_checkpoint=args.teacher_checkpoint,
        dataset_dir=args.dataset_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
    )


if __name__ == "__main__":
    main()
