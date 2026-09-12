"""RL value-head training on self-play outcomes (candidate `silky-snow`).

Self-play NPZ shards store (X=board tensor, y=game outcome from the
side-to-move perspective in {0.0, 0.5, 1.0}). We convert those to the same
3-way WDL targets the flagship value head already uses, so the head keeps one
consistent output space:

    win  -> [1, 0, 0]
    draw -> [0, 1, 0]
    loss -> [0, 0, 1]

Optionally mixes in supervised Stockfish-labelled positions (cp -> WDL via
the Lichess logistic model) to keep the value anchored to absolute strength
rather than only to our own self-play policy.

  training/.venv/Scripts/python.exe training/scripts/train_rl_value.py \
      --selfplay training/datasets/selfplay_v1 \
      --checkpoint training/checkpoints/flagship_v7_value/best_flagship.pt \
      --out training/checkpoints/silky_snow_v1
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
import torch.nn.functional as functional
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.models.flagship import ChessFlagshipNet  # noqa: E402


def score_to_wdl(cp: float) -> list[float]:
    """Lichess/Stockfish logistic model: cp -> [win, draw, loss] probs."""
    p_win = 1.0 / (1.0 + 10.0 ** (-cp / 400.0))
    p_draw = 0.40 * math.exp(-((cp / 300.0) ** 2))
    p_win_adj = max(0.0, p_win - p_draw / 2.0)
    p_loss_adj = max(0.0, (1.0 - p_win) - p_draw / 2.0)
    total = p_win_adj + p_draw + p_loss_adj
    return [p_win_adj / total, p_draw / total, p_loss_adj / total]


def outcome_to_wdl(y: float) -> list[float]:
    """Self-play outcome scalar -> one-hot-ish WDL target."""
    if y >= 0.75:
        return [1.0, 0.0, 0.0]
    if y <= 0.25:
        return [0.0, 0.0, 1.0]
    return [0.0, 1.0, 0.0]


def load_selfplay(directory: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load self-play shards -> (X uint8, y outcome float)."""
    shards = sorted(directory.glob("*.npz"))
    if not shards:
        raise SystemExit(f"No self-play shards in {directory}")
    Xs, ys = [], []
    for p in shards:
        with np.load(p) as d:
            Xs.append(d["X"])
            ys.append(d["y"])
    return np.concatenate(Xs), np.concatenate(ys)


def load_supervised(directory: Path, cap: int) -> tuple[np.ndarray, np.ndarray] | None:
    """Load Stockfish-labelled shards -> (X uint8, y cp float). Capped."""
    shards = sorted(directory.glob("*.npz"))
    if not shards:
        return None
    Xs, ys, n = [], [], 0
    for p in shards:
        if n >= cap:
            break
        with np.load(p) as d:
            X, y = d["X"], d["y"]
        take = min(len(y), cap - n)
        Xs.append(X[:take])
        ys.append(y[:take])
        n += take
    return np.concatenate(Xs), np.concatenate(ys)


def build_tensors(
    X_sp: np.ndarray,
    y_sp: np.ndarray,
    sup: tuple[np.ndarray, np.ndarray] | None,
    seed: int,
) -> TensorDataset:
    """Combine self-play + (optional) supervised into one WDL dataset."""
    wdls = [outcome_to_wdl(float(v)) for v in y_sp]
    Xs = [X_sp]
    if sup is not None:
        X_sup, y_cp = sup
        wdls.extend(score_to_wdl(float(v)) for v in y_cp)
        Xs.append(X_sup)
    X = np.concatenate(Xs).astype(np.float32)
    W = np.array(wdls, dtype=np.float32)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(X))
    return TensorDataset(torch.from_numpy(X[idx]), torch.from_numpy(W[idx]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selfplay", type=Path, required=True)
    ap.add_argument(
        "--supervised",
        type=Path,
        default=None,
        help="optional Stockfish-labelled dir to anchor absolute strength",
    )
    ap.add_argument("--sup-cap", type=int, default=400_000)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--freeze-trunk", action="store_true")
    ap.add_argument("--seed", type=int, default=20260913)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}")

    X_sp, y_sp = load_selfplay(args.selfplay)
    print(
        f"self-play: {len(X_sp)} positions "
        f"(decisive={float((np.abs(y_sp - 0.5) > 0.25).mean()):.2f})"
    )

    sup = None
    if args.supervised is not None:
        sup = load_supervised(args.supervised, args.sup_cap)
        if sup is not None:
            print(f"supervised: {len(sup[0])} positions")

    ds = build_tensors(X_sp, y_sp, sup, args.seed)
    n_val = max(1, int(0.1 * len(ds)))
    n_train = len(ds) - n_val
    train_ds, val_ds = torch.utils.data.random_split(
        ds, [n_train, n_val], generator=torch.Generator().manual_seed(args.seed)
    )
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)
    print(f"train={n_train} val={n_val}")

    model = ChessFlagshipNet().to(device)
    ckpt = torch.load(args.checkpoint, map_location="cpu")
    model.load_state_dict(ckpt["model_state_dict"])
    print(f"init from {args.checkpoint}")

    for name, p in model.named_parameters():
        if name.startswith("policy_head") or (
            args.freeze_trunk and (name.startswith("stem") or name.startswith("tower"))
        ):
            p.requires_grad = False
    n_tr = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"trainable: {n_tr:,}")

    opt = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=1e-4
    )
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs * len(train_loader))

    args.out.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, float]] = []
    best, stale = float("inf"), 0

    for ep in range(args.epochs):
        model.train()
        run = 0.0
        t0 = time.perf_counter()
        for xb, wb in train_loader:
            xb, wb = xb.to(device), wb.to(device)
            opt.zero_grad(set_to_none=True)
            _, logits = model(xb)
            smooth = wb * 0.9 + 0.1 / 3.0
            loss = -(smooth * functional.log_softmax(logits, dim=-1)).sum(dim=1).mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            run += float(loss)

        model.eval()
        vwce = vn = 0.0
        with torch.no_grad():
            for xb, wb in val_loader:
                xb, wb = xb.to(device), wb.to(device)
                _, logits = model(xb)
                vwce += float(-(wb * functional.log_softmax(logits, dim=-1)).sum(dim=1).sum())
                vn += xb.size(0)
        vwce /= max(1, vn)
        run /= max(1, len(train_loader))
        dt = time.perf_counter() - t0
        history.append({"epoch": ep, "train": run, "val_wce": vwce})
        print(f"ep{ep:02d} train={run:.4f} val_wce={vwce:.4f} ({dt:.0f}s)", flush=True)

        if vwce < best - 1e-4:
            best, stale = vwce, 0
            torch.save(
                {"model_state_dict": model.state_dict(), "val_wce": vwce, "epoch": ep},
                args.out / "best_flagship.pt",
            )
        else:
            stale += 1
            if stale >= args.patience:
                print(f"early stop at epoch {ep}")
                break

    (args.out / "history.json").write_text(json.dumps(history, indent=1))
    print(f"best val_wce={best:.4f} -> {args.out / 'best_flagship.pt'}")


if __name__ == "__main__":
    main()
