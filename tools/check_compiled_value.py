"""Independent dense/sparse and compiled-array parity for compact value weights."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import random
import sys
from pathlib import Path

import chess
import numpy as np
from numpy.typing import NDArray


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    sys.path.insert(0, str(args.agent.resolve()))
    runtime = importlib.import_module("compact_value")
    compiled = importlib.import_module("compiled_eval")
    core = importlib.import_module("core")
    rng = random.Random(20260919)
    board = chess.Board()
    worst = 0.0
    for _ in range(500):
        if board.is_game_over() or board.ply() >= 150:
            board = chess.Board()
        tensor: NDArray[np.float32] = np.zeros((12, 8, 8), dtype=np.float32)
        for square, piece in board.piece_map().items():
            plane = piece.piece_type - 1 + (0 if piece.color else 6)
            tensor[plane, square // 8, square % 8] = 1
        x = tensor.reshape(768)
        mirror = np.concatenate((tensor[6:], tensor[:6]))[:, ::-1, :].reshape(768)
        a = np.maximum(0, x @ runtime.W1 + runtime.B1)
        b = np.maximum(0, mirror @ runtime.W1 + runtime.B1)
        dense = float(400 * np.tanh(float((a - b) @ runtime.W2) * 0.5))
        sparse = runtime.residual_white(board)
        worst = max(worst, abs(dense - sparse))
        assert abs(dense - sparse) < 0.001
        assert abs(sparse + runtime.residual_white(board.mirror())) < 0.001
        assert abs(sparse) <= 400
        array, side, _, _ = core.encode_board(board)
        assert compiled.evaluate_array(array, side, 0.25) == runtime.evaluate(board)
        board.push(rng.choice(list(board.legal_moves)))
    result = {"positions": 500, "max_dense_sparse_cp": worst,
              "compiled_integer_parity": True, "symmetry_bounds": True,
              "weights_sha256": hashlib.sha256(
                  (args.agent / "weights/compact_value.npz").read_bytes()).hexdigest(),
              "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
