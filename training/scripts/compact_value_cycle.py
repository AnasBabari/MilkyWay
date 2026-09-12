"""Prepare a frozen classical-residual dataset and GPU-train a sparse value model.

This is the supervised initialization for subsequent outcome-based self-play updates.
Never uses a random position split: retains the source train/validation game splits.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def prepare(args: argparse.Namespace) -> None:
    sys.path.insert(0, str(args.baseline.resolve()))
    sys.path.append(str(ROOT))
    evaluation = importlib.import_module("evaluation")
    from training.data.representation import tensor_to_board

    assert evaluation.fast_eval_active(), "Frozen baseline must use its normal evaluator"
    if args.out.exists():
        raise SystemExit("Use a fresh output directory; existing evidence is immutable")
    args.out.mkdir(parents=True)
    manifest: dict[str, Any] = {"baseline": str(args.baseline.resolve()), "sources": {},
                "baseline_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in args.baseline.glob("*.py")},
                "purpose": "supervised initialization; no strength or RL success claim"}
    for split in ("train", "val", "test"):
        features, anchors, labels = [], [], []
        for path in sorted((args.data / split).glob("*.npz")):
            manifest["sources"][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            with np.load(path) as data:
                for tensor, value, mask in zip(
                    data["boards"], data["value_targets"], data["value_masks"], strict=True
                ):
                    if not mask:
                        continue
                    board = tensor_to_board(tensor)
                    if not board.is_valid() or board.is_game_over():
                        continue
                    sign = 1.0 if board.turn else -1.0
                    cp = float(600 * np.arctanh(np.clip(value, -0.9866, 0.9866))) * sign
                    features.append(tensor[:12].reshape(768))
                    anchors.append(float(evaluation.evaluate(board)) * sign)
                    labels.append(cp)
            print(f"prepared {split}: {len(labels)}", flush=True)
        assert labels, split
        np.savez_compressed(args.out / f"{split}.npz", x=np.asarray(features, np.uint8),
                            anchor=np.asarray(anchors, np.float32),
                            target=np.asarray(labels, np.float32))
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))


def train(args: argparse.Namespace) -> None:
    import torch
    from torch import nn

    if not torch.cuda.is_available():
        raise SystemExit("CUDA required for this training run")
    if args.out.exists():
        raise SystemExit("Use a fresh single-writer checkpoint directory")
    args.out.mkdir(parents=True)
    torch.manual_seed(args.seed)
    torch.set_num_threads(1)
    device = torch.device("cuda")
    permutation: np.ndarray = np.arange(768).reshape(12, 8, 8)
    permutation = np.concatenate((permutation[6:], permutation[:6]))[:, ::-1, :].reshape(768)
    mirror = torch.tensor(permutation.copy(), device=device)

    class Residual(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.hidden = nn.Linear(768, args.hidden)
            self.output = nn.Linear(args.hidden, 1)
            nn.init.zeros_(self.output.weight)
            nn.init.zeros_(self.output.bias)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            a = self.output(torch.relu(self.hidden(x)))
            b = self.output(torch.relu(self.hidden(x[:, mirror])))
            return 400.0 * torch.tanh((a - b).squeeze(-1) * 0.5)

    tensors = {}
    for split in ("train", "val"):
        with np.load(args.data / f"{split}.npz") as d:
            tensors[split] = tuple(torch.tensor(d[k], device=device, dtype=torch.float32)
                                   for k in ("x", "anchor", "target"))
    model = Residual().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    x, anchor, target = tensors["train"]
    vx, va, vt = tensors["val"]
    best = float("inf")
    history = []
    baseline_mae = float((va - vt).abs().mean())
    print(f"CUDA {torch.cuda.get_device_name(0)}; samples={len(x)}; "
          f"baseline validation MAE={baseline_mae:.2f}", flush=True)
    for epoch in range(args.epochs):
        model.train()
        order = torch.randperm(len(x), device=device)
        # The pinned PyTorch stubs omit annotations on these tensor methods.
        for indices in order.split(args.batch):  # type: ignore[no-untyped-call]
            predicted = anchor[indices] + model(x[indices])
            error = (predicted - target[indices]) / 400.0
            loss = torch.nn.functional.huber_loss(error, torch.zeros_like(error), delta=0.5)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()  # type: ignore[no-untyped-call]
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        model.eval()
        with torch.no_grad():
            prediction = torch.cat([va[i:i+args.batch] + model(vx[i:i+args.batch])
                                    for i in range(0, len(vx), args.batch)])
            mae = float((prediction - vt).abs().mean())
        history.append({"epoch": epoch, "validation_mae_cp": mae})
        print(f"epoch={epoch} val_mae={mae:.3f}", flush=True)
        if mae < best:
            best = mae
            state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            torch.save({"state": state, "hidden": args.hidden, "epoch": epoch},
                       args.out / "best.pt")
            np.savez(args.out / "compact_value.npz",
                     w1=state["hidden.weight"].numpy().T.copy(),
                     b1=state["hidden.bias"].numpy(), w2=state["output.weight"].numpy()[0],
                     mirror=permutation, scale=np.float32(400))
        (args.out / "history.json").write_text(json.dumps(history, indent=2))
    (args.out / "manifest.json").write_text(json.dumps({
        "seed": args.seed, "hidden": args.hidden, "epochs": args.epochs,
        "learning_rate": args.lr, "gpu": torch.cuda.get_device_name(0),
        "baseline_validation_mae_cp": baseline_mae, "best_validation_mae_cp": best,
        "dataset_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in args.data.glob("*.npz")},
        "trainer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "stage": "supervised initialization; self-play update and arenas pending",
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "train"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=ROOT / "experiments/silky_snow")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--hidden", type=int, default=16)
    parser.add_argument("--batch", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else train)(args)


if __name__ == "__main__":
    main()
