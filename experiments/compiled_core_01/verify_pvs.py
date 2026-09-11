"""TT equivalence, context safety, repeated-hit and clock probes."""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path

import chess
import numpy as np
from compiled_search import LIMIT, MATE, position_key
from compiled_search import search as reference
from core import encode_board
from pvs_search import history_context, negamax, pack_mate, search, unpack_mate


def main():
    reference(chess.Board(), 0, 1)
    search(chess.Board(), 0, 1)
    for ply in range(20):
        for score in (0, 100, -100, MATE - 20, -MATE + 20):
            assert unpack_mate(pack_mate(score, ply), ply) == score
    rng = random.Random(20260916)
    board = chess.Board()
    rows = []
    for _ in range(12):
        for _ in range(2):
            if board.is_game_over():
                board = chess.Board()
            board.push(rng.choice(list(board.legal_moves)))
        if board.is_game_over():
            board = chess.Board()
        base = reference(board, 20, 3)
        result = search(board, 20, 3)
        assert base["depth"] == result["depth"] == 3
        assert base["score"] == result["score"], (board.fen(), base, result)
        assert chess.Move.from_uci(result["move"]) in board.legal_moves
        timed = search(board, 0.02, 30)
        assert timed["elapsed_s"] < 0.12, timed
        rows.append({"fen": board.fen(), "reference": base, "tt": result})
    # Same context must hit; poisoned entry from another reversible history
    # must never supply a score, even though it can still order its legal move.
    board = chess.Board()
    a, side, rights, ep = encode_board(board)
    key = position_key(a, side, rights, ep)
    history = np.zeros(LIMIT + 2, dtype=np.uint64)
    history[0] = key
    keys = np.zeros(1024, dtype=np.uint64)
    contexts = np.zeros(1024, dtype=np.uint64)
    entries = np.zeros((1024, 4), dtype=np.int64)
    stats = np.zeros(3, dtype=np.int64)

    def run():
        return negamax(a, side, rights, ep, 0, 2, -MATE - 1, MATE + 1, 0,
                       history, 1, stats, time.perf_counter() + 30, 0.25, 0,
                       keys, contexts, entries)

    first = run()
    stats[:] = 0
    assert run() == first and stats[2] == 1 and stats[0] == 1
    slot = int(key & np.uint64(1023))
    contexts[slot] ^= np.uint64(1)
    entries[slot, 2] = 12345
    stats[:] = 0
    assert run()[0] == first[0] and stats[0] > 1
    # Histories with equal count but different occurrence membership differ.
    h1 = np.array([1, 2, 1, 3], dtype=np.uint64)
    h2 = np.array([2, 1, 2, 3], dtype=np.uint64)
    assert history_context(h1, 4, 3, 0) != history_context(h2, 4, 3, 0)
    assert history_context(h1, 4, 3, 0) != history_context(h1, 4, 2, 0)
    root = Path(__file__).parent
    result = {"positions": rows, "context_and_mate_checks": True,
              "sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                         for name in ("compiled_search.py", "pvs_search.py", "verify_pvs.py")}}
    (root / "pvs_verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"positions": len(rows), "context_and_mate_checks": True,
                      "reference_nodes": sum(r["reference"]["nodes"] for r in rows),
                      "tt_nodes": sum(r["tt"]["nodes"] for r in rows)}, indent=2))


if __name__ == "__main__":
    main()
