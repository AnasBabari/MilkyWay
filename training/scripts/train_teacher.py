# ruff: noqa: E402
"""MilkyWay M17 — ResNet Teacher Training Pipeline.

Features:
  - AdamW optimizer with warmup + cosine decay
  - FP16 Automatic Mixed Precision (AMP) via torch.amp.autocast and GradScaler
  - Multi-task masked loss (Policy + WDL + Centipawns)
  - Full checkpointing with git commit, optimizer, scheduler, scaler, step, metrics
  - Seamless resume support
  - Validation tracking: Top-1/3/5, MRR, WDL acc, Value MAE
  - Failure benchmark tracking (LARPMAXX position ranking)
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch
from torch.amp.autocast_mode import autocast
from torch.amp.grad_scaler import GradScaler
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader

from training.data.dataset import ShardedChessDataset, create_dataloader
from training.metrics.evaluator import compute_batch_metrics, evaluate_failure_positions
from training.models.losses import MultiTaskChessLoss
from training.models.teacher import ChessTeacher, create_teacher


def get_git_commit() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def get_cosine_schedule_with_warmup(
    optimizer: torch.optim.Optimizer,
    num_warmup_steps: int,
    num_training_steps: int,
    min_lr_ratio: float = 0.05,
) -> LambdaLR:
    def lr_lambda(current_step: int) -> float:
        if current_step < num_warmup_steps:
            return float(current_step) / float(max(1, num_warmup_steps))
        progress = float(current_step - num_warmup_steps) / float(
            max(1, num_training_steps - num_warmup_steps)
        )
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return min_lr_ratio + (1.0 - min_lr_ratio) * cosine

    return LambdaLR(optimizer, lr_lambda)


def evaluate(
    model: ChessTeacher,
    val_loader: DataLoader[dict[str, torch.Tensor]],
    loss_fn: MultiTaskChessLoss,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    agg_metrics: dict[str, float] = {}
    batches = 0
    dev_type = "cuda" if device.type == "cuda" else "cpu"
    amp_enabled = device.type == "cuda"

    with torch.no_grad():
        for batch in val_loader:
            boards = batch["board"].to(device, non_blocking=True)
            with autocast(device_type=dev_type, dtype=torch.float16, enabled=amp_enabled):
                p_log, w_log, val = model(boards)
                loss_dict = loss_fn(p_log, w_log, val, batch)
                total_loss += loss_dict["loss"].item()

            b_metrics = compute_batch_metrics(p_log, w_log, val, batch)
            for k, v in b_metrics.items():
                agg_metrics[k] = agg_metrics.get(k, 0.0) + v
            batches += 1

    model.train()
    results = {"val_loss": total_loss / max(1, batches)}
    for k, v in agg_metrics.items():
        if not k.endswith("_count"):
            results[f"val_{k}"] = v / max(1, batches)
    return results


def train_teacher(
    dataset_dir: Path,
    arch: str = "teacher_b",
    batch_size: int = 512,
    epochs: int = 5,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    warmup_steps: int = 100,
    save_every_steps: int = 500,
    checkpoint_dir: Path = Path("training/checkpoints/teacher"),
    resume_path: Path | None = None,
    device_str: str = "cuda" if torch.cuda.is_available() else "cpu",
    num_workers: int = 0,
    seed: int = 42,
) -> Path:
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device(device_str)
    dev_type = "cuda" if device.type == "cuda" else "cpu"
    amp_enabled = device.type == "cuda"

    # 1. Load shards
    train_shards = sorted(list((dataset_dir / "train").glob("*.npz")))
    val_shards = sorted(list((dataset_dir / "val").glob("*.npz")))
    if not train_shards:
        raise FileNotFoundError(f"No training shards found in {dataset_dir / 'train'}")

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

    # 2. Model, Optimizer, Loss
    model = create_teacher(arch).to(device)
    loss_fn = MultiTaskChessLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scaler = GradScaler("cuda", enabled=(device.type == "cuda"))

    total_steps = len(train_loader) * epochs
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    start_step = 0
    samples_seen = 0
    best_policy_top1 = 0.0

    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Resume if requested
    if resume_path is not None and resume_path.is_file():
        print(f"Resuming training from checkpoint {resume_path}...")
        ckpt = torch.load(resume_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        if "optimizer_state_dict" in ckpt:
            optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        if "scheduler_state_dict" in ckpt:
            scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        if "scaler_state_dict" in ckpt:
            scaler.load_state_dict(ckpt["scaler_state_dict"])
        start_step = ckpt.get("step", 0)
        samples_seen = ckpt.get("samples_seen", 0)
        best_policy_top1 = ckpt.get("best_policy_top1", 0.0)
        print(f"Resumed at step {start_step}, samples seen: {samples_seen}")

    val_samples_count = len(val_dataset) if val_dataset else 0
    print("=== Starting Teacher Training ===")
    print(f"Arch: {arch} ({model.count_parameters():,} parameters)")
    print(f"Train samples: {len(train_dataset):,}, Val samples: {val_samples_count:,}")
    print(f"Batch size: {batch_size}, Total steps: {total_steps}, Epochs: {epochs}")
    dev_name = torch.cuda.get_device_name(0) if device.type == "cuda" else "CPU"
    print(f"Device: {device} ({dev_name})")

    global_step = start_step
    start_time = time.time()

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0

        for batch in train_loader:
            global_step += 1
            optimizer.zero_grad(set_to_none=True)

            boards = batch["board"].to(device, non_blocking=True)
            with autocast(device_type=dev_type, dtype=torch.float16, enabled=amp_enabled):
                p_log, w_log, val = model(boards)
                loss_dict = loss_fn(p_log, w_log, val, batch)
                loss = loss_dict["loss"]

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            samples_seen += boards.shape[0]
            epoch_loss += loss.item()

            if global_step % 50 == 0 or global_step == 1:
                cur_lr = scheduler.get_last_lr()[0]
                throughput = samples_seen / max(1.0, time.time() - start_time)
                p_loss_val = loss_dict['policy_loss'].item()
                w_loss_val = loss_dict['wdl_loss'].item()
                v_loss_val = loss_dict['value_loss'].item()
                print(
                    f"Epoch {epoch+1}/{epochs} | Step {global_step}/{total_steps} | "
                    f"Loss: {loss.item():.4f} (P: {p_loss_val:.3f}, W: {w_loss_val:.3f}, "
                    f"V: {v_loss_val:.3f}) | LR: {cur_lr:.2e} | {throughput:.0f} samples/s"
                )

            if global_step % save_every_steps == 0:
                ckpt_path = checkpoint_dir / f"teacher_step_{global_step:06d}.pt"
                torch.save(
                    {
                        "step": global_step,
                        "samples_seen": samples_seen,
                        "epoch": epoch,
                        "arch": arch,
                        "config": asdict(model.config),
                        "model_state_dict": model.state_dict(),
                        "optimizer_state_dict": optimizer.state_dict(),
                        "scheduler_state_dict": scheduler.state_dict(),
                        "scaler_state_dict": scaler.state_dict(),
                        "git_commit": get_git_commit(),
                    },
                    ckpt_path,
                )

        # Epoch evaluation
        if val_loader:
            val_results = evaluate(model, val_loader, loss_fn, device)
            print(
                f"--- Epoch {epoch+1} Validation --- "
                f"Loss: {val_results['val_loss']:.4f} | "
                f"P Top-1: {val_results.get('val_policy_top1', 0.0):.3f} | "
                f"P Top-3: {val_results.get('val_policy_top3', 0.0):.3f} | "
                f"P MRR: {val_results.get('val_policy_mrr', 0.0):.3f} | "
                f"WDL Acc: {val_results.get('val_wdl_acc', 0.0):.3f} | "
                f"Val MAE: {val_results.get('val_value_mae', 0.0):.3f}"
            )

            # Check failure positions
            failures = evaluate_failure_positions(model, device=str(device))
            for f_item in failures:
                blunder_str = (
                    f"Blunder {f_item['blunder_move']} rank: "
                    f"{f_item['blunder_rank']}/{f_item['total_legal_moves']}"
                )
                good_str = f"Best good {f_item['best_good_move']} rank: {f_item['best_good_rank']}"
                print(
                    f"Failure Benchmark [{f_item['name']}]: {blunder_str} | "
                    f"{good_str} | Safe retreat preferred: {f_item['good_preferred_over_blunder']}"
                )

            top1 = val_results.get("val_policy_top1", 0.0)
            if top1 > best_policy_top1:
                best_policy_top1 = top1
                best_path = checkpoint_dir / "best_policy.pt"
                torch.save(
                    {
                        "step": global_step,
                        "samples_seen": samples_seen,
                        "arch": arch,
                        "config": asdict(model.config),
                        "model_state_dict": model.state_dict(),
                        "val_metrics": val_results,
                        "git_commit": get_git_commit(),
                    },
                    best_path,
                )

    # Save final checkpoint
    final_path = checkpoint_dir / "latest.pt"
    torch.save(
        {
            "step": global_step,
            "samples_seen": samples_seen,
            "arch": arch,
            "config": asdict(model.config),
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "scaler_state_dict": scaler.state_dict(),
            "git_commit": get_git_commit(),
        },
        final_path,
    )
    print(f"Teacher training complete. Checkpoints saved to {checkpoint_dir}")
    return final_path


def main() -> None:
    parser = argparse.ArgumentParser(description="MilkyWay Teacher training script.")
    parser.add_argument("--dataset-dir", type=Path, default=Path("training/datasets/smoke_50k"))
    parser.add_argument("--arch", type=str, default="teacher_b")
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--warmup-steps", type=int, default=100)
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("training/checkpoints/teacher"))
    parser.add_argument("--resume", type=Path, default=None)
    args = parser.parse_args()

    train_teacher(
        dataset_dir=args.dataset_dir,
        arch=args.arch,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        warmup_steps=args.warmup_steps,
        checkpoint_dir=args.checkpoint_dir,
        resume_path=args.resume,
    )


if __name__ == "__main__":
    main()
