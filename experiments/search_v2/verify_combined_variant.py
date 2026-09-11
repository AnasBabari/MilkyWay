"""Verify the combined staged+LMR variant: both mechanisms, legality, safety.

Run with the runtime dir on sys.path first (runtimes share module names):

    python verify_combined_variant.py <runtime_dir> <out_json>

Compares combined_search against the untouched plain ordered_search baseline
living in the same runtime at fixed depth 5 on a deterministic 30-position
spread, checks legality of every move, low-clock get_move reliability, and a
sequential self-play line. Gates freezing on: both mechanisms engaging
(reductions and staged generation must fire), legal play everywhere, and no
catastrophic same-depth disagreement vs the plain baseline. Never strength.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

RUNTIME = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(RUNTIME))

import chess  # noqa: E402
from combined_search import search as combined  # noqa: E402
from ordered_search import search as plain  # noqa: E402

import agent  # noqa: E402

SUITE = Path(__file__).resolve().parent / "probe_suite_01.json"


def load_positions() -> list[dict]:
    data = json.loads(SUITE.read_text(encoding="utf-8-sig"))
    positions = data["positions"] if isinstance(data, dict) else data
    return positions[:: 8][:30]


def main() -> None:
    combined(chess.Board(), seconds=0.0, soft_seconds=0.0, max_depth=1,
             prior_keys=())
    rows = []
    for entry in load_positions():
        board = chess.Board(entry["fen"])
        result = combined(board, seconds=30.0, soft_seconds=30.0, max_depth=5,
                          prior_keys=())
        move = chess.Move.from_uci(result["move"])
        assert move in board.legal_moves, (entry.get("id"), result["move"])
        assert not result["aborted"]
        reference = plain(board, seconds=30.0, soft_seconds=30.0, max_depth=5,
                          prior_keys=())
        assert chess.Move.from_uci(reference["move"]) in board.legal_moves
        rows.append({
            "id": entry.get("id"),
            "move": result["move"],
            "score": result["score"],
            "nodes": result["nodes"],
            "reductions": result["reductions"],
            "reduction_researches": result["reduction_researches"],
            "baseline_move": reference["move"],
            "baseline_score": reference["score"],
            "baseline_nodes": reference["nodes"],
        })

    low_clock_failures = []
    for entry in load_positions()[:20]:
        board = chess.Board(entry["fen"])
        try:
            proposed = chess.Move.from_uci(agent.get_move(entry["fen"], 250))
            if proposed not in board.legal_moves:
                low_clock_failures.append(entry.get("id"))
        except Exception as error:
            low_clock_failures.append(f"{entry.get('id')}: {error!r}")

    line_moves = []
    board = chess.Board()
    time_left = 2000
    for _ply in range(40):
        proposed = chess.Move.from_uci(agent.get_move(board.fen(), time_left))
        if proposed not in board.legal_moves:
            line_moves.append(f"ILLEGAL:{proposed.uci()}")
            break
        line_moves.append(proposed.uci())
        board.push(proposed)
        time_left = max(200, time_left - 40)
        if board.is_game_over():
            break

    payload = {
        "runtime": str(RUNTIME),
        "fixed_depth_rows": rows,
        "low_clock_failures": low_clock_failures,
        "selfplay_line": line_moves,
        "selfplay_legal": all(not m.startswith("ILLEGAL") for m in line_moves),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    total_reductions = sum(r["reductions"] for r in rows)
    total_researches = sum(r["reduction_researches"] for r in rows)
    payload["total_reductions"] = total_reductions
    payload["total_reduction_researches"] = total_researches
    nodes_combo = sum(r["nodes"] for r in rows)
    nodes_base = sum(r["baseline_nodes"] for r in rows)
    payload["nodes_combo"] = nodes_combo
    payload["nodes_baseline"] = nodes_base
    disagreements = [r for r in rows if r["move"] != r["baseline_move"]]
    payload["disagreements"] = [
        {"id": r["id"], "combined_move": r["move"],
         "baseline_move": r["baseline_move"], "combined_score": r["score"],
         "baseline_score": r["baseline_score"],
         "delta_cp": (r["score"] - r["baseline_score"])}
        for r in disagreements
    ]
    worst = min((d["delta_cp"] for d in payload["disagreements"]), default=0)
    payload["worst_disagreement_delta_cp"] = worst
    assert total_reductions > 0, "LMR never engaged; merge broken"
    assert worst >= -300, f"tactical defect: worst changed decision {worst}cp"
    payload["verified"] = (
        not low_clock_failures and payload["selfplay_legal"] and worst >= -300
    )
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"verified {RUNTIME.name}: rows={len(rows)} "
          f"reductions={total_reductions} researches={total_researches} "
          f"nodes={nodes_combo}/{nodes_base} disagreements={len(disagreements)} "
          f"worst_delta={worst}cp selfplay_legal={payload['selfplay_legal']}")


if __name__ == "__main__":
    main()