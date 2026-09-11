"""Broad LMR probe with disabled-path parity, history and counter checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import chess

HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=2.0)
    parser.add_argument("--depth", type=int, default=5)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=False)
    runtime = HERE / "diagnostic_runtime_01"
    sys.path.insert(0, str(runtime))
    from core import encode_board
    from diagnostic_search import position_key, search
    from ordered_search import search as reference

    suite_path = HERE / "probe_suite_01.json"
    suite = json.loads(suite_path.read_text())
    warm_start = time.perf_counter()
    reference(chess.Board(), 0, 1)
    search(chess.Board(), 0, 1, lmr_enabled=False)
    warm_s = time.perf_counter() - warm_start
    (args.out / "manifest.json").write_text(json.dumps({
        "suite_sha256": hashlib.sha256(suite_path.read_bytes()).hexdigest(),
        "runtime_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in runtime.glob("*.py")},
        "depth": args.depth, "seconds_per_arm": args.seconds,
        "warm_s": warm_s, "purpose": "diagnostic, not strength or controlled timing"}, indent=2))
    rows = []
    for index, row in enumerate(suite["positions"]):
        board = chess.Board(row["history_start_fen"])
        prior = []
        for uci in row["history_uci"]:
            array, side, rights, ep = encode_board(board)
            prior.append(int(position_key(array, side, rights, ep)))
            board.push_uci(uci)
        assert board.fen() == row["fen"]
        results = {}
        for label in ("reference", "disabled", "lmr"):
            start = time.perf_counter()
            if label == "reference":
                result = reference(board, args.seconds, args.depth, prior_keys=prior)
            else:
                result = search(board, args.seconds, args.depth, prior_keys=prior,
                                lmr_enabled=label == "lmr")
                m = result["metrics"]
                assert m["qnodes"] <= result["nodes"]
                assert (m["tt_cutoffs"] <= m["tt_context_depth_hits"]
                        <= m["tt_position_hits"] <= m["tt_probes"])
                assert m["first_move_beta_cutoffs"] <= m["beta_cutoffs"]
                assert result["reduction_researches"] <= result["reductions"]
            result["end_to_end_s"] = time.perf_counter() - start
            assert chess.Move.from_uci(result["move"]) in board.legal_moves
            results[label] = result
        a, b = results["reference"], results["disabled"]
        parity_checked = not a["aborted"] and not b["aborted"]
        if parity_checked:
            assert all(a[key] == b[key] for key in ("score", "move", "depth", "nodes")), row["id"]
        entry = {"id": row["id"], "categories": row["categories"],
                 "parity_checked": parity_checked, "results": results}
        rows.append(entry)
        with (args.out / "positions.jsonl").open("a") as stream:
            stream.write(json.dumps(entry) + "\n")
        if (index + 1) % 10 == 0:
            print(f"{index + 1}/{len(suite['positions'])} positions", flush=True)
    completed = [r for r in rows if not r["results"]["disabled"]["aborted"]
                 and not r["results"]["lmr"]["aborted"]]
    summary = {"positions": len(rows), "parity_cases": sum(r["parity_checked"] for r in rows),
               "comparable_completed": len(completed),
               "disabled_nodes": sum(r["results"]["disabled"]["nodes"] for r in completed),
               "lmr_nodes": sum(r["results"]["lmr"]["nodes"] for r in completed),
               "move_changes": sum(r["results"]["disabled"]["move"] != r["results"]["lmr"]["move"]
                                   for r in completed),
               "score_changes": sum(r["results"]["disabled"]["score"]
                                    != r["results"]["lmr"]["score"]
                                    for r in completed), "strength_claim": False}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
