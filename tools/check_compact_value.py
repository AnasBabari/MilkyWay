"""Check CPU sparse inference against dense exported-weight inference."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import random
import sys
import time
from pathlib import Path

import chess
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.agent.resolve()))
    runtime = importlib.import_module("compact_value")
    representation = importlib.import_module("root_policy")
    rng = random.Random(20260908)
    board = chess.Board()
    positions = []
    worst = 0.0
    for _ in range(500):
        if board.is_game_over() or board.ply() >= 100:
            board = chess.Board()
        board.push(rng.choice(list(board.legal_moves)))
        positions.append(board.copy())
        tensor = representation.board_to_tensor(board)[:12].astype(np.float32)
        mirrored = np.concatenate((tensor[6:], tensor[:6]))[:, ::-1, :].reshape(768)
        a = np.maximum(0, tensor.reshape(768) @ runtime.W1 + runtime.B1)
        b = np.maximum(0, mirrored @ runtime.W1 + runtime.B1)
        dense = float(400 * np.tanh(float((a - b) @ runtime.W2) * 0.5))
        sparse = runtime.residual_white(board)
        worst = max(worst, abs(dense - sparse))
        assert abs(dense - sparse) < 0.001
        assert abs(sparse + runtime.residual_white(board.mirror())) < 0.001
        assert abs(sparse) <= 400
    timings = {}
    for name, fn in (("classical", runtime.classical_evaluate), ("compact", runtime.evaluate)):
        start = time.perf_counter()
        for _ in range(20):
            for position in positions:
                fn(position)
        timings[name + "_us"] = (time.perf_counter() - start) * 100
    report = {"positions": 500, "max_parity_error_cp": worst, "timing": timings,
              "sha256": {str(p.relative_to(args.agent)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(args.agent.rglob("*"))
                         if p.is_file() and p.suffix in (".py", ".onnx", ".npz")}}
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps({"positions": 500, "max_error": worst, **timings}, indent=2))


if __name__ == "__main__":
    main()
