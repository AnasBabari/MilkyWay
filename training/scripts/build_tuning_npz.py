# ruff: noqa: E402
"""Build M16 tuning NPZ from SF-labelled value shards.

X = 50 white-perspective features, y = white-perspective Stockfish cp
(recovered exactly from tanh labels: cp = 600*atanh(v)), fixed = non-tunable
PST/mop term. Game-level splits inherited from the value dataset (no leakage).

  .venv/Scripts/python.exe training/scripts/build_tuning_npz.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess

from training.data.representation import tensor_to_board
from training.scripts.extract_features import extract_features_white

SRC = Path("training/datasets/master_value_v2")
OUT = Path("training/datasets/tuning_master_value_v2.npz")


def split_arrays(split: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    xs: list[list[float]] = []
    ys: list[float] = []
    fixed: list[float] = []
    skipped = 0
    for path in sorted((SRC / split).glob("shard_*.npz")):
        data = np.load(path)
        boards = data["boards"]
        vals = data["value_targets"]
        masks = data["value_masks"]
        for i in range(len(boards)):
            if masks[i] == 0:
                skipped += 1
                continue
            try:
                board = tensor_to_board(boards[i])
            except ValueError:
                skipped += 1
                continue
            if not board.is_valid():
                skipped += 1
                continue
            feats, fix = extract_features_white(board)
            v = float(np.clip(vals[i], -0.9867, 0.9867))
            cp_stm = 600.0 * float(np.arctanh(v))
            cp_white = cp_stm if board.turn == chess.WHITE else -cp_stm
            xs.append(feats)
            ys.append(float(np.clip(cp_white, -1500.0, 1500.0)))
            fixed.append(fix)
    n_feat = len(xs[0]) if xs else 0
    print(f"{split}: {len(xs)} positions, {n_feat} features, skipped {skipped}", flush=True)
    return (
        np.array(xs, dtype=np.float32),
        np.array(ys, dtype=np.float32),
        np.array(fixed, dtype=np.float32),
        n_feat,
    )


def main() -> None:
    payload: dict[str, np.ndarray] = {}
    for split in ("train", "val", "test"):
        x, y, f, n = split_arrays(split)
        assert n == 50, f"expected 50 features, got {n}"
        payload[f"X_{split}"] = x
        payload[f"y_{split}"] = y
        payload[f"fixed_{split}"] = f
    # Dynamic array keys never include NumPy's separately typed allow_pickle option.
    np.savez_compressed(OUT, **cast(dict[str, Any], payload))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
