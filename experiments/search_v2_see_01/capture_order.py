"""Original material-exchange estimate for move ordering, never move pruning.

Follow the cheapest legal recapturer, choosing the lowest square on ties.
Each side may decline a recapture. This is an ordering heuristic, not minimax:
alternative attackers, intermediate moves, and underpromotions are not explored.
"""
from __future__ import annotations

import numpy as np
from core import attacked, king_square, make_move, unmake_move
from numba import njit

VALUES = (0, 100, 320, 330, 500, 900, 20000)


@njit(cache=False)
def reaches(board, origin, target):
    """Whether a piece attacks target given current occupancy."""
    piece = int(board[origin])
    kind = abs(piece)
    dr, df = target // 8 - origin // 8, target % 8 - origin % 8
    ar, af = abs(dr), abs(df)
    if kind == 1:
        return dr == (1 if piece > 0 else -1) and af == 1
    if kind == 2:
        return (ar == 1 and af == 2) or (ar == 2 and af == 1)
    if kind == 6:
        return max(ar, af) == 1
    diagonal = ar == af and ar > 0
    straight = (dr == 0) != (df == 0)
    if not ((kind in (3, 5) and diagonal) or (kind in (4, 5) and straight)):
        return False
    step_r = (1 if dr > 0 else -1) if dr else 0
    step_f = (1 if df > 0 else -1) if df else 0
    r, f = origin // 8 + step_r, origin % 8 + step_f
    while r * 8 + f != target:
        if board[r * 8 + f]:
            return False
        r += step_r
        f += step_f
    return True


@njit(cache=False)
def least_legal_capture(board, target, side):
    best_move, best_value = 0, 30000
    if abs(int(board[target])) == 6:
        return 0
    for origin in range(64):
        piece = int(board[origin])
        if piece * side <= 0 or VALUES[abs(piece)] >= best_value:
            continue
        if not reaches(board, origin, target):
            continue
        promotion = 5 if abs(piece) == 1 and target // 8 in (0, 7) else 0
        move = origin | (target << 6) | (promotion << 12)
        undo = make_move(board, move, 0, -1)
        legal = not attacked(board, king_square(board, side), -side)
        unmake_move(board, move, undo)
        if legal:
            best_move, best_value = move, VALUES[abs(piece)]
    return best_move


@njit(cache=False)
def exchange_value(board, move, rights, ep):
    """Material gain under a legal least-attacker recapture sequence."""
    work = board.copy()
    origin, target, promotion = move & 63, (move >> 6) & 63, move >> 12
    side = 1 if work[origin] > 0 else -1
    victim = abs(int(work[target]))
    if abs(int(work[origin])) == 1 and target == ep and not victim:
        victim = 1
    gains = np.zeros(33, dtype=np.int64)
    gains[0] = VALUES[victim] + (VALUES[promotion] - VALUES[1] if promotion else 0)
    make_move(work, move, rights, ep)
    count = 0
    side = -side
    while count < 32:
        reply = least_legal_capture(work, target, side)
        if not reply:
            break
        promoted = reply >> 12
        count += 1
        gains[count] = (VALUES[abs(int(work[target]))]
                        + (VALUES[promoted] - VALUES[1] if promoted else 0)
                        - gains[count - 1])
        make_move(work, reply, 0, -1)
        side = -side
    while count > 0:
        gains[count - 1] = -max(-gains[count - 1], gains[count])
        count -= 1
    return gains[0]
