"""Small team-trained positional residual, evaluated sparsely on a single CPU."""

from __future__ import annotations

import math
from pathlib import Path

import chess
import numpy as np
from numba import njit

from evaluation import evaluate as classical_evaluate

with np.load(Path(__file__).parent / "weights/compact_value.npz") as _data:
    W1 = _data["w1"].copy()
    B1 = _data["b1"].copy()
    W2 = _data["w2"].copy()


@njit(cache=False)
def residual_kernel(pawns, knights, bishops, rooks, queens, kings, white, black, w1, b1, w2):
    a = b1.copy()
    b = b1.copy()
    occupied = white | black
    for square in range(64):
        bit = np.uint64(1) << np.uint64(square)
        if not occupied & bit:
            continue
        piece = (0 if pawns & bit else 1 if knights & bit else 2 if bishops & bit
                 else 3 if rooks & bit else 4 if queens & bit else 5)
        color = 0 if white & bit else 6
        index = (piece + color) * 64 + square
        mirror = (piece + 6 - color) * 64 + (square ^ 56)
        for h in range(len(b1)):
            a[h] += w1[index, h]
            b[h] += w1[mirror, h]
    result = 0.0
    for h in range(len(b1)):
        result += (max(0.0, a[h]) - max(0.0, b[h])) * w2[h]
    return 400.0 * math.tanh(result * 0.5)


def residual_white(board: chess.Board) -> float:
    return float(residual_kernel(
        np.uint64(board.pawns), np.uint64(board.knights), np.uint64(board.bishops),
        np.uint64(board.rooks), np.uint64(board.queens), np.uint64(board.kings),
        np.uint64(board.occupied_co[chess.WHITE]), np.uint64(board.occupied_co[chess.BLACK]),
        W1, B1, W2,
    ))


def evaluate(board: chess.Board) -> int:
    correction = round(0.25 * residual_white(board))
    return classical_evaluate(board) + (correction if board.turn else -correction)


# JIT compile within the import budget, before the match clock starts.
residual_white(chess.Board())
