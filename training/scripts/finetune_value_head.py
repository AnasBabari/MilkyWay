"""Fine-tune the value head on high-quality Stockfish-evaluated positions.

Loads a flagship checkpoint, freezes policy + trunk, and trains only the
value head against WDL targets derived from Stockfish cp scores.

  training/.venv/Scripts/python.exe training/scripts/finetune_value_head.py \
      --checkpoint training/checkpoints/flagship_v6/best_flagship.pt \
      --data training/datasets/lichess_eval_v1 \
      --out training/checkpoints/flagship_v7_value \
      --epochs 10 --batch-size 2048 --lr 1e-4
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.models.flagship import ChessFlagshipNet  # noqa: E402


def score_to_wdl(cp: float) -> list[float]:
    """Convert centipawn score to approximate WDL probabilities."""
    p_win = 1.0 / (1.0 + 10.0 ** (-cp / 400.0))
    p_draw = 0.40 * math.exp(-((cp / 300.0) ** 2))
    p_win_adj = max(0.0, p_win - p_draw / 2.0)
    p_loss_adj = max(0.0, (1.0 - p_win) - p_draw / 2.0)
    total = p_win_adj + p_draw + p_loss_adj
    return [float(p_win_adj / total), float(p_draw / total), float(p_loss_adj / total)]


class EvalDataset(Dataset):
    """Dataset from NPZ shards with board tensors and cp values."""

    def __init__(self, shard_paths: list[Path]) -> None:
        self.boards: list[np.ndarray] = []
        self.wdls: list[np.ndarray] = []
        for path in shard_paths:
            with np.load(path) as data:
                X = data["X"].astype(np.float32) / 1.0  # keep as float32
                y = data["y"].astype(np.float32)
                for i in range(len(y)):
                    self.boards.append(X[i])
                    self.wdls.append(np.array(score_to_wdl(float(y[i])), dtype=np.float32))

    def __len__(self) -> int:
        return len(self.boards)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "board": torch.from_numpy(self.boards[idx]),
            "wdl": torch.from_numpy(self.wdls[idx]),
        }


def evaluate(model: ChessFlagshipNet, loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    tot_wce = tot_n = 0.0
    abs_err = abs_n = 0.0
    with torch.no_grad():
        for batch in loader:
            boards = batch["board"].to(device)
            wdl_t = batch["wdl"].to(device)
            _, s_wdl = model(boards)
            wdl_logp = F.log_softmax(s_wdl, dim=-1)
            wce = -(wdl_t * wdl_logp).sum(dim=1)
            tot_wce += float(wce.sum())
            tot_n += boards.size(0)

            pred_wdl = F.softmax(s_wdl, dim=-1)
            pred_e = (pred_wdl[:, 0] + 0.5 * pred_wdl[:, 1]).clamp(0.001, 0.999)
            pred_cp = 400.0 * (pred_e / (1.0 - pred_e)).log10()
            true_e = (wdl_t[:, 0] + 0.5 * wdl_t[:, 1]).clamp(0.001, 0.999)
            true_cp = 400.0 * (true_e / (1.0 - true_e)).log10()
            ae = (pred_cp - true_cp).abs()
            abs_err += float(ae.sum())
            abs_n += boards.size(0)

    return {
        "value_wce": tot_wce / max(1, tot_n),
        "value_mae_cp": abs_err / max(1e-6, abs_n),
    }


def train(args: argparse.Namespace) -> Path:
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}")

    # Load model
    model = ChessFlagshipNet().to(device)
    ckpt = torch.load(args.checkpoint, map_location="cpu")
    model.load_state_dict(ckpt["model_state_dict"])
    print(f"Loaded checkpoint from {args.checkpoint}")

    # Freeze policy head and optionally trunk
    for name, param in model.named_parameters():
        if name.startswith("policy_head"):
            param.requires_grad = False
        elif args.freeze_trunk and (name.startswith("stem") or name.startswith("tower")):
            param.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Trainable params: {trainable:,} / {total:,}")

    # Load data
    shards = sorted(args.data.glob("*.npz"))
    if not shards:
        raise SystemExit(f"No NPZ shards found in {args.data}")

    # Split: 90% train, 10% val
    rng = np.random.RandomState(args.seed)
    indices = np.arange(len(shards))
    rng.shuffle(indices)
    split = int(0.9 * len(shards))
    train_shards = [shards[i] for i in indices[:split]]
    val_shards = [shards[i] for i in indices[split:]]

    print(f"Loading {len(train_shards)} train shards, {len(val_shards)} val shards...")
    train_ds = EvalDataset(train_shards)
    val_ds = EvalDataset(val_shards)
    print(f"Train: {len(train_ds)} positions, Val: {len(val_ds)} positions")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    opt = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.lr,
        weight_decay=1e-4,
    )
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs * len(train_loader))

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
            boards = batch["board"].to(device)
            wdl_t = batch["wdl"].to(device)

            opt.zero_grad(set_to_none=True)
            _, s_wdl = model(boards)
            wdl_logp = F.log_softmax(s_wdl, dim=-1)
            # Label smoothing
            wdl_smooth = wdl_t * 0.9 + 0.1 / 3.0
            loss = -(wdl_smooth * wdl_logp).sum(dim=1).mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            run_loss += float(loss)

        run_loss /= max(1, len(train_loader))
        vm = evaluate(model, val_loader, device)
        val_comp = vm["value_wce"]
        rec = {"epoch": epoch, "train_loss": run_loss, "val_comp": val_comp, **vm}
        history.append(rec)
        dt = time.perf_counter() - t0
        print(
            f"ep{epoch:02d} train={run_loss:.4f} val_wce={vm['value_wce']:.4f} "
            f"vmae_cp={vm['value_mae_cp']:.1f} ({dt:.0f}s)",
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
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--freeze-trunk", action="store_true", help="freeze stem + tower")
    parser.add_argument("--seed", type=int, default=20260907)
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
