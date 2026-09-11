"""LMR toggle equivalence, basic tactical safeguards and work measurements."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import chess
from ordered_search import search as reference
from reduced_search import search


def main():
    reference(chess.Board(), 0, 1)
    search(chess.Board(), 0, 1)
    rng = random.Random(20260920)
    board = chess.Board()
    rows = []
    for _ in range(12):
        for _ in range(3):
            if board.is_game_over():
                board = chess.Board()
            board.push(rng.choice(list(board.legal_moves)))
        if board.is_game_over():
            board = chess.Board()
        baseline = reference(board, 20, 4)
        disabled = search(board, 20, 4, lmr_enabled=False)
        assert baseline["depth"] == disabled["depth"] == 4
        assert baseline["score"] == disabled["score"]
        assert baseline["nodes"] == disabled["nodes"]
        enabled = search(board, 20, 4)
        assert enabled["depth"] == 4 and chess.Move.from_uci(enabled["move"]) in board.legal_moves
        clocked = search(board, 0.02, 30)
        assert clocked["elapsed_s"] < 0.12
        rows.append({"fen": board.fen(), "parent": baseline, "enabled": enabled})
    mates = ["7k/8/5KQ1/8/8/8/8/8 w - - 0 1",
             "8/8/8/8/8/5kq1/8/7K b - - 0 1"]
    for fen in mates:
        board = chess.Board(fen)
        result = search(board, 1, 5)
        board.push_uci(result["move"])
        assert board.is_checkmate()
    root = Path(__file__).parent
    result = {"positions": rows, "disabled_exact_work_and_score": True,
              "basic_mate_checks": True,
              "parent_nodes": sum(r["parent"]["nodes"] for r in rows),
              "reduced_nodes": sum(r["enabled"]["nodes"] for r in rows),
              "score_changes": sum(r["parent"]["score"] != r["enabled"]["score"] for r in rows),
              "reductions": sum(r["enabled"]["reductions"] for r in rows),
              "sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                         for name in ("ordered_search.py", "reduced_search.py",
                                      "verify_reductions.py")}}
    (root / "reduction_verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ("positions", "sha256")},
                     indent=2))


if __name__ == "__main__":
    main()
