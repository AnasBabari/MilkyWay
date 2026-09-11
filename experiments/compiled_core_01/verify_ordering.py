"""Fixed-depth score and work comparison for killer/history ordering."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import chess
from ordered_search import search
from pvs_search import search as reference


def main():
    reference(chess.Board(), 0, 1)
    search(chess.Board(), 0, 1)
    board = chess.Board()
    rng = random.Random(20260918)
    rows = []
    for _ in range(16):
        for _ in range(3):
            if board.is_game_over():
                board = chess.Board()
            board.push(rng.choice(list(board.legal_moves)))
        if board.is_game_over():
            board = chess.Board()
        old = reference(board, 30, 4)
        new = search(board, 30, 4)
        assert old["depth"] == new["depth"] == 4, (old, new)
        assert old["score"] == new["score"], (board.fen(), old, new)
        assert chess.Move.from_uci(new["move"]) in board.legal_moves
        timed = search(board, 0.02, 30)
        assert timed["elapsed_s"] < 0.12
        rows.append({"fen": board.fen(), "pvs": old, "ordered": new})
    result = {"positions": rows,
              "pvs_nodes": sum(row["pvs"]["nodes"] for row in rows),
              "ordered_nodes": sum(row["ordered"]["nodes"] for row in rows),
              "pvs_seconds": sum(row["pvs"]["elapsed_s"] for row in rows),
              "ordered_seconds": sum(row["ordered"]["elapsed_s"] for row in rows)}
    root = Path(__file__).parent
    result["sha256"] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                        for name in ("pvs_search.py", "ordered_search.py", "verify_ordering.py")}
    (root / "ordering_verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ("positions", "sha256")},
                     indent=2))


if __name__ == "__main__":
    main()
