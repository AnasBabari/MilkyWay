"""Use the team's unchanged classical kernel and trained residual from compiled search."""
from __future__ import annotations

import numpy as np
from compact_value import B1, W1, W2, residual_kernel
from numba import njit

import fast_eval as fe
from evaluation import ACTIVE_PARAMS

PARAMS = fe.build_param_vector(ACTIVE_PARAMS)


@njit(cache=False)
def evaluate_array(board, side, coefficient=0.25):
    bits = np.zeros(12, dtype=np.uint64)
    for square in range(64):
        piece = int(board[square])
        if piece:
            index = abs(piece) - 1 + (6 if piece < 0 else 0)
            bits[index] |= np.uint64(1) << np.uint64(square)
    classical = fe._eval_kernel(
        bits[0], bits[1], bits[2], bits[3], bits[4], bits[5],
        bits[6], bits[7], bits[8], bits[9], bits[10], bits[11],
        1 if side == 1 else 0, PARAMS, fe.RAYS, fe.KNIGHT_ATTACKS,
        fe.KING_ATTACKS, fe.PAWN_ATTACKS, fe.PASSER_MASKS, fe.WHITE_PST_SQ,
        fe._BISHOP_DIRS_ARR, fe._ROOK_DIRS_ARR, fe._ALL_DIRS_ARR)
    if coefficient == 0:
        return classical
    white = bits[0] | bits[1] | bits[2] | bits[3] | bits[4] | bits[5]
    black = bits[6] | bits[7] | bits[8] | bits[9] | bits[10] | bits[11]
    residual = residual_kernel(bits[0] | bits[6], bits[1] | bits[7], bits[2] | bits[8],
                               bits[3] | bits[9], bits[4] | bits[10], bits[5] | bits[11],
                               white, black, W1, B1, W2)
    return classical + side * int(np.rint(coefficient * residual))
