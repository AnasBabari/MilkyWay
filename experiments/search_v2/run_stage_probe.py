"""Compare staged quiescence with reference and independent legal move sets."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import chess

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "staged_runtime_01"))
from compiled_search import uci  # noqa: E402
from core import encode_board, legal_moves  # noqa: E402
from ordered_search import position_key  # noqa: E402
from ordered_search import search as reference  # noqa: E402
from staged_search import search  # noqa: E402


def main() -> None:
    out = HERE / "staged_probe_01"
    out.mkdir(exist_ok=False)
    rows = json.loads((HERE / "probe_suite_01.json").read_text())["positions"]
    reference(chess.Board(), 0, 1)
    search(chess.Board(), 0, 1)
    results = []
    for index, row in enumerate(rows):
        board = chess.Board(row["history_start_fen"])
        prior = []
        for move in row["history_uci"]:
            prior.append(int(position_key(*encode_board(board))))
            board.push_uci(move)
        assert board.fen() == row["fen"]
        args = encode_board(board)
        expected = {m.uci() for m in board.legal_moves if board.is_capture(m) or m.promotion}
        actual = {uci(int(m)) for m in legal_moves(*args, True)}
        assert expected == actual, row["id"]
        full = {m.uci() for m in board.legal_moves}
        assert full == {uci(int(m)) for m in legal_moves(*args)}
        first = legal_moves(*args, False, True)
        assert len(first) == int(bool(full))
        pair = {}
        for label, engine in (("reference", reference), ("staged", search)):
            start = time.perf_counter()
            pair[label] = engine(board, 3, 5, prior_keys=prior)
            pair[label]["wall_s"] = time.perf_counter() - start
            assert chess.Move.from_uci(pair[label]["move"]) in board.legal_moves
        a, b = pair["reference"], pair["staged"]
        complete = not a["aborted"] and not b["aborted"]
        if complete:
            assert a["score"] == b["score"] and a["depth"] == b["depth"], row["id"]
        result = {"id": row["id"], "complete": complete, "results": pair}
        results.append(result)
        with (out / "positions.jsonl").open("a") as stream:
            stream.write(json.dumps(result) + "\n")
        if (index + 1) % 20 == 0:
            print(f"{index + 1}/240", flush=True)
    # Terminal detection remains before stand-pat, including 50-move boundary.
    for fen in ("7k/5Q2/6K1/8/8/8/8/8 b - - 100 1", "7k/6Q1/6K1/8/8/8/8/8 b - - 100 1"):
        assert search(chess.Board(fen), 1, 5)["move"] is None
    complete = [r for r in results if r["complete"]]
    summary = {
        "positions": len(results),
        "completed_score_parity": len(complete),
        "legal_capture_and_promotion_sets_match": True,
        "reference_s": sum(r["results"]["reference"]["wall_s"] for r in complete),
        "staged_s": sum(r["results"]["staged"]["wall_s"] for r in complete),
        "reference_nodes": sum(r["results"]["reference"]["nodes"] for r in complete),
        "staged_nodes": sum(r["results"]["staged"]["nodes"] for r in complete),
        "timing_caveat": "Concurrent parent games; diagnostic timing only",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
