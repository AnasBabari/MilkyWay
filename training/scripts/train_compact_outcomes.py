"""GPU outcome-learning update with supervised replay to limit forgetting."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch
from torch import nn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--coefficient", type=float, default=1.0,
                        help="Residual coefficient actually applied by the playing agent")
    parser.add_argument("--outcome-weight", type=float, default=0.05)
    parser.add_argument("--guard-outcome", action="store_true",
                        help="Do not select epochs that worsen held-out outcome BCE")
    args = parser.parse_args()
    assert 0 < args.coefficient <= 1
    assert args.outcome_weight > 0
    assert torch.cuda.is_available()
    if args.out.exists():
        raise SystemExit("Refusing to overwrite a training run")
    args.out.mkdir(parents=True)
    torch.set_num_threads(1)
    torch.manual_seed(args.seed)
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    width = checkpoint["hidden"]
    permutation: np.ndarray = np.arange(768).reshape(12, 8, 8)
    permutation = np.concatenate((permutation[6:], permutation[:6]))[:, ::-1, :].reshape(768)
    mirror = torch.tensor(permutation.copy(), device="cuda")

    class Residual(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.hidden = nn.Linear(768, width)
            self.output = nn.Linear(width, 1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            a = self.output(torch.relu(self.hidden(x)))
            b = self.output(torch.relu(self.hidden(x[:, mirror])))
            return 400 * torch.tanh((a - b).squeeze(-1) * 0.5)

    data = {}
    for kind, directory in (("rl", args.data), ("replay", args.replay)):
        for split in ("train", "val"):
            with np.load(directory / f"{split}.npz") as d:
                data[kind, split] = tuple(torch.tensor(d[k], device="cuda", dtype=torch.float32)
                                         for k in ("x", "anchor", "target"))
    model = Residual().cuda()
    model.load_state_dict(checkpoint["state"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    x, anchor, outcome = data["rl", "train"]
    rx, ra, rt = data["replay", "train"]
    history = []
    best = float("inf")
    initial_bce = float("inf")
    for epoch in range(-1, args.epochs):
        if epoch >= 0:
            model.train()
            for _ in range(max(1, len(rx) // 1024)):
                i = torch.randint(len(x), (256,), device="cuda")
                j = torch.randint(len(rx), (1024,), device="cuda")
                logits = (anchor[i] + args.coefficient * model(x[i])) * (math.log(10) / 400)
                outcome_loss = nn.functional.binary_cross_entropy_with_logits(logits, outcome[i])
                error = (ra[j] + args.coefficient * model(rx[j]) - rt[j]) / 400
                replay_loss = nn.functional.huber_loss(error, torch.zeros_like(error), delta=0.5)
                loss = replay_loss + args.outcome_weight * outcome_loss
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1)
                optimizer.step()
        model.eval()
        with torch.no_grad():
            vx, va, vy = data["rl", "val"]
            val_bce = float(nn.functional.binary_cross_entropy_with_logits(
                (va + args.coefficient * model(vx)) * (math.log(10) / 400), vy))
            sx, sa, st = data["replay", "val"]
            err = torch.cat([(sa[i:i+1024] + args.coefficient * model(sx[i:i+1024]) - st[i:i+1024])
                             for i in range(0, len(sx), 1024)])
            val_mae = float(err.abs().mean())
            metric = float(nn.functional.huber_loss(err / 400, torch.zeros_like(err), delta=0.5))
            metric += args.outcome_weight * val_bce
        if epoch == -1:
            initial_bce = val_bce
        history.append({"epoch": epoch, "outcome_bce": val_bce,
                        "supervised_mae_cp": val_mae, "selection_loss": metric})
        print(json.dumps(history[-1]), flush=True)
        if metric < best and (not args.guard_outcome or val_bce <= initial_bce):
            best = metric
            state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            torch.save({"state": state, "hidden": width, "epoch": epoch}, args.out / "best.pt")
            np.savez(args.out / "compact_value.npz", w1=state["hidden.weight"].numpy().T.copy(),
                     b1=state["hidden.bias"].numpy(), w2=state["output.weight"].numpy()[0],
                     mirror=permutation, scale=np.float32(400))
        (args.out / "history.json").write_text(json.dumps(history, indent=2))
    (args.out / "manifest.json").write_text(json.dumps({
        "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "data_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for directory in (args.data, args.replay) for p in directory.glob("*.npz")},
        "trainer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "gpu": torch.cuda.get_device_name(0), "seed": args.seed,
        "learning": "Monte Carlo outcome update plus supervised replay",
        "outcome_weight": args.outcome_weight, "learning_rate": 0.0001,
        "guard_outcome": args.guard_outcome,
        "runtime_residual_coefficient": args.coefficient,
    }, indent=2))


if __name__ == "__main__":
    main()
