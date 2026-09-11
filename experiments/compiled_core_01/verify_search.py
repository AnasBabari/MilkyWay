"""Independent python-chess reference, terminal rules and deadline checks."""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path

import chess
import numpy as np
from compact_value import evaluate
from compiled_search import LIMIT, MATE, insufficient, negamax, position_key, search, uci
from core import encode_board


def reference(board, depth, alpha, beta, ply=0):
    moves = list(board.legal_moves)
    check = board.is_check()
    if not moves:
        return -MATE + ply if check else 0
    if board.halfmove_clock >= 100 or board.is_repetition(3) or board.is_insufficient_material():
        return 0
    if ply >= LIMIT:
        return evaluate(board)
    best = -MATE - 1
    if depth <= 0 and not check:
        best = evaluate(board)
        if best >= beta:
            return best
        alpha = max(alpha, best)
    for move in moves:
        if depth <= 0 and not check and not board.is_capture(move) and not move.promotion:
            continue
        board.push(move)
        value = -reference(board, depth - 1, -beta, -alpha, ply + 1)
        board.pop()
        best = max(best, value)
        alpha = max(alpha, value)
        if alpha >= beta:
            break
    return best


def score_position(board, depth, repetitions=1):
    array, side, rights, ep = encode_board(board)
    before = array.copy()
    history = np.zeros(LIMIT + 5, dtype=np.uint64)
    history[:repetitions] = position_key(array, side, rights, ep)
    stats = np.zeros(2, dtype=np.int64)
    value, move = negamax(array, side, rights, ep, board.halfmove_clock,
                          depth, -MATE - 1, MATE + 1, 0, history, repetitions,
                          stats, time.perf_counter() + 60, 0.25, 0)
    assert not stats[1], "reference test timed out"
    assert np.array_equal(before, array)
    return value, move


def main():
    started = time.perf_counter()
    search(chess.Board(), 0, 1)  # JIT warmup; excluded from deadline checks.
    warmup = time.perf_counter() - started
    terminals = [
        "7k/6Q1/5K2/8/8/8/8/8 b - - 100 1",  # Mate precedes fifty moves.
        "7k/5Q2/5K2/8/8/8/8/8 b - - 0 1",  # Stalemate.
        "7k/8/5K2/8/8/8/8/8 w - - 0 1",
        "7k/8/5K2/8/8/8/8/R7 w - - 100 1",
    ]
    for fen in terminals:
        board = chess.Board(fen)
        assert score_position(board, 2)[0] == reference(board, 2, -MATE - 1, MATE + 1)
    repeat = chess.Board()
    for move in ("g1f3", "g8f6", "f3g1", "f6g8") * 2:
        repeat.push_uci(move)
    assert score_position(repeat, 2, repetitions=3)[0] == 0
    # Legal EP affects repetition, pinned EP does not.
    for fen, differs in [
        ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", True),
        ("k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", False),
    ]:
        a, s, r, ep = encode_board(chess.Board(fen))
        assert (position_key(a, s, r, ep) != position_key(a, s, r, -1)) == differs
    mate = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
    value, move = score_position(mate, 1)
    mate.push_uci(uci(move))
    assert mate.is_checkmate() and value == MATE - 1
    rng = random.Random(20260915)
    board = chess.Board()
    deadlines = []
    for i in range(30):
        for _ in range(3):
            if board.is_game_over():
                board = chess.Board()
            board.push(rng.choice(list(board.legal_moves)))
        if board.is_game_over():
            board = chess.Board()
        a, _, _, _ = encode_board(board)
        assert insufficient(a) == board.is_insufficient_material()
        if i < 12:
            expected = reference(board, 1, -MATE - 1, MATE + 1)
            actual, _ = score_position(board, 1)
            assert actual == expected, (board.fen(), actual, expected)
        result = search(board, 0.02, 30)
        assert chess.Move.from_uci(result["move"]) in board.legal_moves
        assert result["elapsed_s"] < 0.12, result
        deadlines.append(result["elapsed_s"])
    root = Path(__file__).parent
    report = {"reference_positions": 12, "deadline_positions": 30,
              "terminal_and_repetition_checks": True, "warmup_s": warmup,
              "max_20ms_search_s": max(deadlines),
              "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in root.glob("*.py")}}
    (root / "search_verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "sha256"}, indent=2))


if __name__ == "__main__":
    main()
