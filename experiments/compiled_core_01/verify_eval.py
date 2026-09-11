"""Exact integer evaluation parity against the frozen candidate on random legal positions."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import chess
from compact_value import evaluate
from compiled_eval import evaluate_array
from core import encode_board

from evaluation import evaluate as classical


def main():
    rng = random.Random(20260914)
    board = chess.Board()
    for _ in range(2000):
        if board.is_game_over() or board.ply() >= 150:
            board = chess.Board()
        array, side, _, _ = encode_board(board)
        assert evaluate_array(array, side, 0.0) == classical(board), board.fen()
        assert evaluate_array(array, side, 0.25) == evaluate(board), board.fen()
        board.push(rng.choice(list(board.legal_moves)))
    root = Path(__file__).parent
    result = {"positions": 2000, "classical_exact": True, "trained_residual_exact": True,
              "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in root.glob("*.py")},
              "weights_sha256": hashlib.sha256(
                  (root / "weights/compact_value.npz").read_bytes()).hexdigest()}
    (root / "evaluation_verification.json").write_text(json.dumps(result, indent=2))
    print("2000 positions: exact classical and trained-residual evaluation parity")


if __name__ == "__main__":
    main()
