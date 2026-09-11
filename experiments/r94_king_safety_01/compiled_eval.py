"""Use the team's unchanged classical kernel and trained residual from compiled search."""
from __future__ import annotations

import numpy as np
from compact_value import B1, W1, W2, residual_kernel
from numba import njit

import fast_eval as fe
from evaluation import ACTIVE_PARAMS

PARAMS = fe.build_param_vector(ACTIVE_PARAMS)



@njit(cache=False)
def exposed_king_penalty(board, color):
    """Penalize a central king with open approach files against heavy pieces.

    This is a general positional feature, inactive without an enemy queen,
    with lower weight after the enemy rooks have been exchanged.
    """
    king = -1
    queen = False
    rooks = 0
    for square in range(64):
        piece = int(board[square])
        if piece == color * 6:
            king = square
        elif piece == -color * 5:
            queen = True
        elif piece == -color * 4:
            rooks += 1
    if king < 0 or not queen:
        return 0
    file = king % 8
    if file < 3 or file > 4:
        return 0
    rank = king // 8
    relative_rank = rank if color == 1 else 7 - rank
    danger = 20 + min(relative_rank, 3) * 15
    for f in range(file - 1, file + 2):
        protected = False
        for step in (1, 2):
            r = rank + color * step
            if 0 <= r < 8 and board[r * 8 + f] == color:
                protected = True
        if not protected:
            danger += 25
    return danger * (2 + min(rooks, 2)) // 4

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
    classical += side * (exposed_king_penalty(board, -1)
                         - exposed_king_penalty(board, 1))
    if coefficient == 0:
        return classical
    white = bits[0] | bits[1] | bits[2] | bits[3] | bits[4] | bits[5]
    black = bits[6] | bits[7] | bits[8] | bits[9] | bits[10] | bits[11]
    residual = residual_kernel(bits[0] | bits[6], bits[1] | bits[7], bits[2] | bits[8],
                               bits[3] | bits[9], bits[4] | bits[10], bits[5] | bits[11],
                               white, black, W1, B1, W2)
    return classical + side * int(np.rint(coefficient * residual))
