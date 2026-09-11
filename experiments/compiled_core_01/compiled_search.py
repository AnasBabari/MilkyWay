"""Original compiled search prototype. Not yet a promoted playing agent.

The first version deliberately uses full legal generation and no selective
pruning. This gives the optimized search a correctness reference.
"""
from __future__ import annotations

import time

import numpy as np
from compiled_eval import evaluate_array
from core import attacked, encode_board, king_square, legal_moves, make_move, unmake_move
from numba import njit, objmode

MATE = 30000
LIMIT = 96
VALUES = np.array([0, 100, 320, 330, 500, 900, 20000], dtype=np.int64)


@njit(cache=False)
def position_key(board, side, rights, ep):
    # Repetition includes an EP square only when an EP capture is legal.
    effective_ep = -1
    if ep >= 0:
        origin_rank = ep // 8 - side
        for delta in (-1, 1):
            file = ep % 8 + delta
            if 0 <= file < 8 and 0 <= origin_rank < 8:
                origin = origin_rank * 8 + file
                if board[origin] == side:
                    move = origin | (ep << 6)
                    undo = make_move(board, move, rights, ep)
                    valid = not attacked(board, king_square(board, side), -side)
                    unmake_move(board, move, undo)
                    if valid:
                        effective_ep = ep
    key = np.uint64(14695981039346656037)
    for square in range(64):
        key = (key ^ np.uint64(int(board[square]) + 6)) * np.uint64(1099511628211)
    for value in (side + 1, rights, effective_ep + 1):
        key = (key ^ np.uint64(value)) * np.uint64(1099511628211)
    return key


@njit(cache=False)
def insufficient(board):
    minors = 0
    knights = 0
    bishop_colour = -1
    same_bishops = True
    for square in range(64):
        kind = abs(int(board[square]))
        if kind in (1, 4, 5):
            return False
        if kind in (2, 3):
            minors += 1
            if kind == 2:
                knights += 1
            else:
                colour = (square // 8 + square % 8) % 2
                if bishop_colour >= 0 and colour != bishop_colour:
                    same_bishops = False
                bishop_colour = colour
    return minors <= 1 or (knights == 0 and same_bishops)


@njit(cache=False)
def tick(stats, deadline):
    stats[0] += 1
    if stats[0] % 128 == 1:
        with objmode(now="float64"):
            now = time.perf_counter()
        if now >= deadline:
            stats[1] = 1
    return stats[1] != 0


@njit(cache=False)
def order_scores(board, moves, count, ep, preferred):
    scores = np.zeros(count, dtype=np.int64)
    for i in range(count):
        move = moves[i]
        origin, target, promotion = move & 63, (move >> 6) & 63, move >> 12
        victim = abs(int(board[target]))
        if abs(int(board[origin])) == 1 and target == ep:
            victim = 1
        if victim:
            scores[i] = 10000 + 16 * VALUES[victim] - VALUES[abs(int(board[origin]))]
        if promotion:
            scores[i] += 20000 + VALUES[promotion]
        if move == preferred:
            scores[i] += 1000000
    return scores


@njit(cache=False)
def negamax(board, side, rights, ep, halfmove, depth, alpha, beta, ply,
            history, history_count, stats, deadline, coefficient, preferred):
    if tick(stats, deadline):
        return 0, 0
    moves = legal_moves(board, side, rights, ep)
    count = len(moves)
    check = attacked(board, king_square(board, side), -side)
    if count == 0:
        return (-MATE + ply if check else 0), 0
    key = position_key(board, side, rights, ep)
    occurrences = 0
    for i in range(max(0, history_count - halfmove - 1), history_count):
        if history[i] == key:
            occurrences += 1
    if halfmove >= 100 or occurrences >= 3 or insufficient(board):
        return 0, moves[0]
    if ply >= LIMIT:
        return evaluate_array(board, side, coefficient), moves[0]
    best = -MATE - 1
    best_move = moves[0]
    if depth <= 0 and not check:
        best = evaluate_array(board, side, coefficient)
        if best >= beta:
            return best, 0
        alpha = max(alpha, best)
    scores = order_scores(board, moves, count, ep, preferred)
    for i in range(count):
        pick = i
        for j in range(i + 1, count):
            if scores[j] > scores[pick]:
                pick = j
        moves[i], moves[pick] = moves[pick], moves[i]
        scores[i], scores[pick] = scores[pick], scores[i]
        move = moves[i]
        origin, target, promotion = move & 63, (move >> 6) & 63, move >> 12
        pawn = abs(int(board[origin])) == 1
        capture = board[target] != 0 or (pawn and target == ep)
        if depth <= 0 and not check and not capture and promotion == 0:
            continue
        undo = make_move(board, move, rights, ep)
        child_halfmove = 0 if pawn or capture else halfmove + 1
        history[history_count] = position_key(board, -side, undo[7], undo[8])
        value, _ = negamax(board, -side, undo[7], undo[8], child_halfmove,
                           depth - 1, -beta, -alpha, ply + 1, history,
                           history_count + 1, stats, deadline, coefficient, 0)
        value = -value
        unmake_move(board, move, undo)
        if stats[1]:
            return 0, 0
        if value > best:
            best, best_move = value, move
        alpha = max(alpha, value)
        if alpha >= beta:
            break
    return best, best_move


def uci(move: int) -> str:
    origin, target, promotion = move & 63, (move >> 6) & 63, move >> 12
    return (chr(97 + origin % 8) + str(1 + origin // 8)
            + chr(97 + target % 8) + str(1 + target // 8)
            + (" pnbrqk"[promotion] if promotion else ""))


def search(board, seconds: float = 1.0, max_depth: int = 20,
           coefficient: float = 0.25, prior_keys=()):
    """Iterative deepening; prior_keys excludes the supplied current position.

    Caller must warm this function before any clocked invocation. Current
    prototype intentionally returns diagnostic fields alongside its move.
    """
    array, side, rights, ep = encode_board(board)
    original = array.copy()
    moves = legal_moves(array, side, rights, ep)
    count = len(moves)
    if not count:
        return {"move": None, "depth": 0, "nodes": 0, "score": None}
    history = np.zeros(len(prior_keys) + LIMIT + 2, dtype=np.uint64)
    history[:len(prior_keys)] = prior_keys
    history[len(prior_keys)] = position_key(array, side, rights, ep)
    stats = np.zeros(2, dtype=np.int64)
    start = time.perf_counter()
    deadline = start + max(0.0, seconds)
    best, score, completed = int(moves[0]), None, 0
    for depth in range(1, max_depth + 1):
        value, move = negamax(array, side, rights, ep, board.halfmove_clock,
                              depth, -MATE - 1, MATE + 1, 0, history,
                              len(prior_keys) + 1, stats, deadline, coefficient, best)
        if stats[1]:
            break
        best, score, completed = int(move), int(value), depth
        if abs(value) >= MATE - LIMIT or time.perf_counter() >= deadline:
            break
    assert np.array_equal(array, original), "search failed to restore board"
    return {"move": uci(best), "depth": completed, "nodes": int(stats[0]),
            "score": score, "elapsed_s": time.perf_counter() - start,
            "aborted": bool(stats[1])}
