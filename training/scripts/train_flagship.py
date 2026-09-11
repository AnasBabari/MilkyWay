# ruff: noqa: E402
"""MilkyWay flagship — fresh GPU pretrain of the joint policy + value net.

Warm-starts trunk + policy head from best_student.pt, trains the value head
from scratch against Stockfish tanh(cp/600) labels, and fine-tunes jointly.

  training/.venv/Scripts/python.exe training/scripts/train_flagship.py \
      --epochs 30 --batch-size 1024 --out training/checkpoints/flagship
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F  # noqa: N812
from torch.amp.autocast_mode import autocast
from torch.amp.grad_scaler import GradScaler
from torch.utils.data import DataLoader

from training.data.dataset import ShardedChessDataset, create_dataloader
from training.models.flagship import ChessFlagshipNet, load_policy_warm_start

DATASET_DIR = Path("training/datasets/master_balanced_32k")
WARM_START = Path("training/checkpoints/student/best_student.pt")
TEMPERATURE = 2.0


def masked_mean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    denom = mask.sum().clamp_min(1e-6)
    return (values * mask).sum() / denom


def evaluate(
    model: ChessFlagshipNet,
    loader: DataLoader[dict[str, torch.Tensor]],
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    tot_ce = tot_kd = tot_vmse = tot_w = 0.0
    top1_c = top1_n = 0
    abs_err = abs_n = 0.0
    with torch.no_grad():
        for batch in loader:
            boards = batch["board"].to(device)
            p_idx = batch["policy_idx"].to(device)
            p_mask = batch["policy_mask"].to(device)
            s_idx = batch["soft_idx"].to(device)
            s_pr = batch["soft_prob"].to(device)
            s_mask = batch["soft_mask"].to(device)
            n = boards.size(0)

            s_logits, s_wdl = model(boards)
            ce = F.cross_entropy(s_logits, p_idx, reduction="none")
            t_logp = F.log_softmax(s_logits / TEMPERATURE, dim=-1)
            kd = F.kl_div(
                t_logp.gather(1, s_idx.clamp_min(0)),
                s_pr,
                reduction="none",
            ).sum(dim=1)
            wdl_logp = F.log_softmax(s_wdl, dim=-1)
            wce = -(batch["wdl"].to(device) * wdl_logp).sum(dim=1)
            w_mask = batch["wdl_mask"].to(device)

            tot_ce += float(masked_mean(ce, p_mask)) * n
            tot_kd += float(masked_mean(kd, s_mask)) * n
            tot_vmse += float(masked_mean(wce, w_mask)) * n
            tot_w += n
            top1_c += int(((s_logits.argmax(1) == p_idx) * p_mask.bool()).sum())
            top1_n += int(p_mask.bool().sum())
            with torch.no_grad():
                pred_wdl = F.softmax(s_wdl.detach(), dim=-1)
                pred_e = (pred_wdl[:, 0] + 0.5 * pred_wdl[:, 1]).clamp(0.001, 0.999)
                pred_cp = 400.0 * (pred_e / (1.0 - pred_e)).log10()
                true_wdl = batch["wdl"].to(device)
                true_e = (true_wdl[:, 0] + 0.5 * true_wdl[:, 1]).clamp(0.001, 0.999)
                true_cp = 400.0 * (true_e / (1.0 - true_e)).log10()
            ae = (pred_cp - true_cp).abs() * w_mask
            abs_err += float(ae.sum())
            abs_n += float(w_mask.sum())
    return {
        "policy_ce": tot_ce / max(1, tot_w),
        "policy_kd": tot_kd / max(1, tot_w),
        "value_mse": tot_vmse / max(1, tot_w),
        "policy_top1": top1_c / max(1, top1_n),
        "value_mae_cp": abs_err / max(1e-6, abs_n),
    }


def train(args: argparse.Namespace) -> Path:
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}")
    if device.type != "cuda":
        print("WARNING: training on CPU will be slow")

    model = ChessFlagshipNet().to(device)
    print(f"parameters: {model.count_parameters():,}")
    if args.cold:
        print("cold start: training from scratch (no warm start)")
    elif args.warm_start.is_file():
        load_policy_warm_start(model, str(args.warm_start), full=args.full_warm_start)
    else:
        print("WARNING: warm-start checkpoint missing, training from scratch")

    train_ds = ShardedChessDataset(sorted((args.data / "train").glob("*.npz")), preload=True)
    val_ds = ShardedChessDataset(sorted((args.data / "val").glob("*.npz")), preload=True)
    train_loader = create_dataloader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = create_dataloader(val_ds, batch_size=args.batch_size, shuffle=False)
    print(f"train={len(train_ds)} val={len(val_ds)} steps/epoch={len(train_loader)}")

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    total_steps = len(train_loader) * args.epochs
    warmup = min(200, total_steps // 10)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt,
        lambda s: min(1.0, (s + 1) / max(1, warmup))
        * 0.5
        * (1.0 + math.cos(math.pi * s / max(1, total_steps))),
    )
    scaler = GradScaler("cuda", enabled=(device.type == "cuda"))

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, float]] = []
    best_val = float("inf")
    stale = 0

    for epoch in range(args.epochs):
        model.train()
        run_loss = 0.0
        t0 = time.perf_counter()
        for batch in train_loader:
            boards = batch["board"].to(device, non_blocking=True)
            p_idx = batch["policy_idx"].to(device)
            p_mask = batch["policy_mask"].to(device)
            s_idx = batch["soft_idx"].to(device)
            s_pr = batch["soft_prob"].to(device)
            s_mask = batch["soft_mask"].to(device)

            opt.zero_grad(set_to_none=True)
            with autocast(device_type=device.type, dtype=torch.float16,
                          enabled=(device.type == "cuda")):
                s_logits, s_wdl = model(boards)
                ce = masked_mean(F.cross_entropy(s_logits, p_idx, reduction="none"), p_mask)
                kd = masked_mean(
                    F.kl_div(
                        F.log_softmax(s_logits / TEMPERATURE, dim=-1).gather(1, s_idx.clamp_min(0)),
                        s_pr,
                        reduction="none",
                    ).sum(dim=1),
                    s_mask,
                )
                # Decisive positions (|tanh value| large) are rare but critical:
                # upweight their value loss so the head cannot ignore the tails.
                with torch.no_grad():
                    v_abs = batch["value"].to(device).abs()
                    v_weight = 1.0 + 1.0 * v_abs.clamp_max(1.0)
                # Label smoothing on WDL targets: prevents one-hot collapse
                # pressure from confident Stockfish tails.
                wdl_t = batch["wdl"].to(device) * 0.9 + 0.1 / 3.0
                wce = masked_mean(
                    -(wdl_t * F.log_softmax(s_wdl, dim=-1)).sum(dim=1) * v_weight,
                    batch["wdl_mask"].to(device),
                )
                loss = ce + 0.5 * kd + 1.0 * wce
                scaled: torch.Tensor = scaler.scale(loss)
                # torch stubs leave Tensor.backward untyped; the tensor type above
                # is exact, so this ignore covers only the stub gap.
                scaled.backward()  # type: ignore[no-untyped-call]
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            run_loss += float(loss)
        run_loss /= max(1, len(train_loader))
        vm = evaluate(model, val_loader, device)
        val_comp = vm["policy_ce"] + 0.5 * vm["policy_kd"] + vm["value_mse"]
        rec = {"epoch": epoch, "train_loss": run_loss, "val_comp": val_comp, **vm}
        history.append(rec)
        dt = time.perf_counter() - t0
        print(
            f"ep{epoch:02d} train={run_loss:.4f} val_ce={vm['policy_ce']:.4f} "
            f"val_kd={vm['policy_kd']:.4f} val_vmse={vm['value_mse']:.4f} "
            f"top1={vm['policy_top1']:.3f} vmae_cp={vm['value_mae_cp']:.1f} ({dt:.0f}s)",
            flush=True,
        )
        if val_comp < best_val - 1e-4:
            best_val = val_comp
            stale = 0
            torch.save(
                {"model_state_dict": model.state_dict(), "val_comp": val_comp, "epoch": epoch},
                out / "best_flagship.pt",
            )
        else:
            stale += 1
            if stale >= args.patience:
                print(f"early stop at epoch {epoch}")
                break
    (out / "history.json").write_text(json.dumps(history, indent=1))
    print(f"best val_comp={best_val:.4f} -> {out / 'best_flagship.pt'}")
    return out / "best_flagship.pt"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATASET_DIR)
    parser.add_argument("--warm-start", type=Path, default=WARM_START)
    parser.add_argument("--out", type=Path, default=Path("training/checkpoints/flagship"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--full-warm-start", action="store_true")
    parser.add_argument("--cold", action="store_true", help="fresh pretrain: skip warm start entirely")
    parser.add_argument("--seed", type=int, default=7)
    train(parser.parse_args())


if __name__ == "__main__":
    main()
