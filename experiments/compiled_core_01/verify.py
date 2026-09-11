"""Compare the new move generator and reversible state with python-chess."""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path

import chess
import numpy as np
from core import encode_board, legal_moves, make_move, perft, unmake_move


def decode(move):
    return chess.Move(move & 63, (move >> 6) & 63, promotion=(move >> 12) or None)


def reference_perft(board, depth):
    if depth == 0:
        return 1
    total = 0
    for move in board.legal_moves:
        board.push(move)
        total += reference_perft(board, depth - 1)
        board.pop()
    return total


def main():
    cases = [
        (chess.STARTING_FEN, 4),
        ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 3),
        ("8/6bb/8/8/R1pP2k1/4P3/P7/K7 b - d3 0 1", 3),
        ("n1n5/PPPk4/8/8/8/8/4Kppp/5N1N w - - 0 1", 3),
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", 3),
    ]
    perft(*encode_board(chess.Board()), 1)
    reports = []
    for fen, depth in cases:
        board = chess.Board(fen)
        assert board.is_valid()
        state = encode_board(board)
        before = state[0].copy()
        start = time.perf_counter()
        actual = perft(*state, depth)
        seconds = time.perf_counter() - start
        expected = reference_perft(board, depth)
        assert actual == expected, (fen, actual, expected)
        assert np.array_equal(state[0], before)
        reports.append({"fen": fen, "depth": depth, "nodes": actual,
                        "compiled_seconds": seconds})
        print(json.dumps(reports[-1]), flush=True)
    rng = random.Random(20260913)
    board = chess.Board()
    transitions = 0
    for _ in range(1000):
        if board.is_game_over() or board.ply() > 150:
            board = chess.Board()
        state = encode_board(board)
        before = state[0].copy()
        actual = legal_moves(*state)
        assert {decode(int(m)) for m in actual} == set(board.legal_moves), board.fen()
        assert np.array_equal(state[0], before)
        for encoded in actual:
            move = decode(int(encoded))
            undo = make_move(state[0], encoded, state[2], state[3])
            board.push(move)
            after = encode_board(board)
            assert np.array_equal(state[0], after[0]), (board.fen(), move)
            assert undo[7:] == after[2:], (board.fen(), move, undo, after[2:])
            board.pop()
            unmake_move(state[0], encoded, undo)
            assert np.array_equal(state[0], before)
            transitions += 1
        board.push(rng.choice(list(board.legal_moves)))
    result = {"perft": reports, "random_positions": 1000, "transitions": transitions,
              "core_sha256": hashlib.sha256(
                  Path(__file__).with_name("core.py").read_bytes()).hexdigest(),
              "status": "move generation prototype verified; no search or strength claim"}
    Path(__file__).with_name("verification.json").write_text(json.dumps(result, indent=2))
    print(f"Passed 1000 legal-position comparisons and {transitions} reversible transitions")


if __name__ == "__main__":
    main()
