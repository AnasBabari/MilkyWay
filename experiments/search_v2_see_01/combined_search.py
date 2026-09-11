"""Combined late-move-reduction and staged-generation search.

Only later quiet non-checking moves in narrow-window nodes are reduced.
An alpha improvement triggers full-depth re-search. Staged quiescence
generation (captures and check evasions first, quiet moves only on demand)
is preserved verbatim from the staged variant. Null-move pruning
(R=2/3, conservative zugzwang guards) is added; see has_non_pawn_material.
This is heuristic pruning;
playing strength must be tested, not inferred from shallow score agreement.
"""
from __future__ import annotations

import time

import numpy as np
from capture_order import VALUES, exchange_value
from compiled_eval import evaluate_array
from compiled_search import LIMIT, MATE, insufficient, order_scores, position_key, tick, uci
from core import attacked, encode_board, king_square, legal_moves, make_move, unmake_move
from numba import njit


@njit(cache=False)
def history_context(history, count, halfmove, ply):
    # Repetition depends on occurrence counts, not the order of earlier positions.
    context = np.uint64(halfmove + 1) * np.uint64(0x9E3779B97F4A7C15)
    context ^= np.uint64(ply + 1) * np.uint64(0xD6E8FEB86659FD93)
    for i in range(max(0, count - halfmove - 1), count):
        value = history[i]
        value ^= value >> np.uint64(30)
        value *= np.uint64(0xBF58476D1CE4E5B9)
        value ^= value >> np.uint64(27)
        value *= np.uint64(0x94D049BB133111EB)
        value ^= value >> np.uint64(31)
        context += value
    return context


@njit(cache=False)
def pack_mate(value, ply):
    if value >= MATE - LIMIT:
        return value + ply
    if value <= -MATE + LIMIT:
        return value - ply
    return value


@njit(cache=False)
def unpack_mate(value, ply):
    if value >= MATE - LIMIT:
        return value - ply
    if value <= -MATE + LIMIT:
        return value + ply
    return value

@njit(cache=False)
def has_non_pawn_material(board, side):
    # Zugzwang guard: with king+pawns only, passing is often best, so a
    # null-move cutoff would be unsound. Any N/B/R/Q of our colour allows it.
    for square in range(64):
        piece = int(board[square])
        if piece * side > 0 and abs(piece) >= 2 and abs(piece) <= 5:
            return True
    return False



@njit(cache=False)
def negamax(board, side, rights, ep, halfmove, depth, alpha, beta, ply,
            history, history_count, stats, deadline, coefficient, preferred,
            tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,
            null_ok):
    if tick(stats, deadline):
        return 0, 0
    check = attacked(board, king_square(board, side), -side)
    if depth <= 0 and not check:
        moves = legal_moves(board, side, rights, ep, True)
        if len(moves) == 0:
            # Preserve stalemate detection without validating every quiet move.
            moves = legal_moves(board, side, rights, ep, False, True)
    else:
        moves = legal_moves(board, side, rights, ep)
    count = len(moves)
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
    original_alpha = alpha
    context = history_context(history, history_count, halfmove, ply)
    slot = int(key & np.uint64(len(tt_keys) - 1))
    if depth > 0 and tt_data[slot, 1] and tt_keys[slot] == key:
        preferred = tt_data[slot, 3]
        if tt_context[slot] == context and tt_data[slot, 0] == depth:
            value = unpack_mate(tt_data[slot, 2], ply)
            bound = tt_data[slot, 1]
            if bound == 1 or (bound == 2 and value >= beta) or (bound == 3 and value <= alpha):
                stats[2] += 1
                return value, preferred
    if (depth >= 3 and not check and null_ok and beta < MATE - LIMIT
            and evaluate_array(board, side, coefficient) >= beta
            and has_non_pawn_material(board, side)):
        # Null-move pruning: verify the position is so good that even passing
        # keeps it above beta. No history update for the pass (standard):
        # a false repetition draw inside the null tree fails low (safe side)
        # except in vanishingly rare exact-3x key repeats with beta <= 0.
        null_depth = depth - 1 - (3 if depth >= 6 else 2)
        nvalue, _ = negamax(board, -side, rights, 0, halfmove + 1,
                            null_depth, -beta, -beta + 1, ply + 1, history,
                            history_count, stats, deadline, coefficient, 0,
                            tt_keys, tt_context, tt_data, killers, move_history,
                            lmr_enabled, False)
        if not stats[1] and -nvalue >= beta:
            stats[5] += 1
            return beta, preferred
    best = -MATE - 1
    best_move = moves[0]
    if depth <= 0 and not check:
        best = evaluate_array(board, side, coefficient)
        if best >= beta:
            return best, 0
        alpha = max(alpha, best)
    scores = order_scores(board, moves, count, ep, preferred)
    side_index = 1 if side == 1 else 0
    for i in range(count):
        move = moves[i]
        origin, target = move & 63, (move >> 6) & 63
        quiet = (board[target] == 0 and move >> 12 == 0
                 and not (abs(int(board[origin])) == 1 and target == ep))
        # A lower-valued victim does not guarantee a profitable exchange.
        # Demote losing captures behind quiet moves; retain every legal move.
        # Promotions and the TT move keep their existing priority.
        victim = abs(int(board[target]))
        attacker = abs(int(board[origin]))
        if (victim and move >> 12 == 0 and move != preferred
                and VALUES[attacker] > VALUES[victim]):
            stats[6] += 1
            if exchange_value(board, move, rights, ep) < 0:
                scores[i] -= 30000
                stats[7] += 1
        if quiet and move != preferred:
            if move == killers[ply, 0]:
                scores[i] += 9500
            elif move == killers[ply, 1]:
                scores[i] += 9000
            else:
                scores[i] += move_history[side_index, origin, target]
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
        if i == 0 or depth <= 0:
            value, _ = negamax(board, -side, undo[7], undo[8], child_halfmove,
                               depth - 1, -beta, -alpha, ply + 1, history,
                               history_count + 1, stats, deadline, coefficient, 0,
                               tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,
                               True)
        else:
            reduced_depth = depth - 1
            reduce = (lmr_enabled and beta == alpha + 1 and depth >= 3 and i >= 4
                      and not check and not capture and promotion == 0
                      and move != killers[ply, 0] and move != killers[ply, 1]
                      and not attacked(board, king_square(board, -side), side))
            if reduce:
                reduced_depth = max(1, depth - (3 if depth >= 6 and i >= 10 else 2))
                stats[3] += 1
            value, _ = negamax(board, -side, undo[7], undo[8], child_halfmove,
                               reduced_depth, -alpha - 1, -alpha, ply + 1, history,
                               history_count + 1, stats, deadline, coefficient, 0,
                               tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,
                               True)
            if reduce and not stats[1] and -value > alpha:
                stats[4] += 1
                value, _ = negamax(board, -side, undo[7], undo[8], child_halfmove,
                                   depth - 1, -alpha - 1, -alpha, ply + 1, history,
                                   history_count + 1, stats, deadline, coefficient, 0,
                                   tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,
                                True)
            if not stats[1] and alpha < -value < beta:
                value, _ = negamax(board, -side, undo[7], undo[8], child_halfmove,
                                   depth - 1, -beta, -alpha, ply + 1, history,
                                   history_count + 1, stats, deadline, coefficient, 0,
                                   tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,
                                True)
        value = -value
        unmake_move(board, move, undo)
        if stats[1]:
            return 0, 0
        if value > best:
            best, best_move = value, move
        alpha = max(alpha, value)
        if alpha >= beta:
            if depth > 0 and not capture and promotion == 0:
                if killers[ply, 0] != move:
                    killers[ply, 1] = killers[ply, 0]
                    killers[ply, 0] = move
                bonus = min(1000, depth * depth * 16)
                old = move_history[side_index, origin, target]
                move_history[side_index, origin, target] = old + bonus - old * bonus // 8000
                for j in range(i):
                    earlier = moves[j]
                    f, t = earlier & 63, (earlier >> 6) & 63
                    if (board[t] == 0 and earlier >> 12 == 0
                            and not (abs(int(board[f])) == 1 and t == ep)):
                        old = move_history[side_index, f, t]
                        move_history[side_index, f, t] = old - bonus - old * bonus // 8000
            break
    if depth > 0:
        tt_keys[slot] = key
        tt_context[slot] = context
        tt_data[slot, 0] = depth
        tt_data[slot, 1] = 3 if best <= original_alpha else (2 if best >= beta else 1)
        tt_data[slot, 2] = pack_mate(best, ply)
        tt_data[slot, 3] = best_move
    return best, best_move


def search(board, seconds: float = 1.0, max_depth: int = 20,
           coefficient: float = 0.25, prior_keys=(), soft_seconds: float | None = None,
           lmr_enabled: bool = True):
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
    stats = np.zeros(8, dtype=np.int64)
    tt_keys = np.zeros(1 << 18, dtype=np.uint64)
    tt_context = np.zeros(1 << 18, dtype=np.uint64)
    tt_data = np.zeros((1 << 18, 4), dtype=np.int64)
    killers = np.zeros((LIMIT + 1, 2), dtype=np.int64)
    move_history = np.zeros((2, 64, 64), dtype=np.int64)
    start = time.perf_counter()
    deadline = start + max(0.0, seconds)
    soft_deadline = start + (seconds if soft_seconds is None else soft_seconds)
    best, score, completed = int(moves[0]), None, 0
    for depth in range(1, max_depth + 1):
        value, move = negamax(array, side, rights, ep, board.halfmove_clock,
                              depth, -MATE - 1, MATE + 1, 0, history,
                              len(prior_keys) + 1, stats, deadline, coefficient, best,
                              tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,
                               True)
        if stats[1]:
            break
        best, score, completed = int(move), int(value), depth
        if abs(value) >= MATE - LIMIT or time.perf_counter() >= soft_deadline:
            break
    assert np.array_equal(array, original), "search failed to restore board"
    return {"move": uci(best), "depth": completed, "nodes": int(stats[0]),
            "score": score, "elapsed_s": time.perf_counter() - start,
            "aborted": bool(stats[1]), "tt_hits": int(stats[2]),
            "reductions": int(stats[3]),
             "reduction_researches": int(stats[4]),
             "null_cutoffs": int(stats[5]), "see_calls": int(stats[6]),
             "losing_captures_demoted": int(stats[7])}
