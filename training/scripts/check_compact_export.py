"""Independently compare selected PyTorch checkpoint with its NumPy export."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    cp = torch.load(args.checkpoint_dir / "best.pt", weights_only=True, map_location="cpu")
    state = cp["state"]
    with np.load(args.data) as d:
        x = d["x"][:1024].astype(np.float32)
    with np.load(args.checkpoint_dir / "compact_value.npz") as d:
        mirror = d["mirror"]
        a = np.maximum(0, x @ d["w1"] + d["b1"])
        b = np.maximum(0, x[:, mirror] @ d["w1"] + d["b1"])
        exported = d["scale"] * np.tanh(((a - b) @ d["w2"]) * 0.5)
    tx = torch.from_numpy(x)
    with torch.no_grad():
        def forward(z: torch.Tensor) -> torch.Tensor:
            hidden = torch.relu(torch.nn.functional.linear(
                z, state["hidden.weight"], state["hidden.bias"]))
            return torch.nn.functional.linear(hidden, state["output.weight"], state["output.bias"])
        direct = 400 * torch.tanh((forward(tx) - forward(tx[:, mirror])).squeeze(-1) * 0.5)
    worst = float(np.max(np.abs(exported - direct.numpy())))
    assert worst < 0.001
    report = {"selected_epoch": cp["epoch"], "positions": len(x), "max_error_cp": worst}
    (args.checkpoint_dir / "export_verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
