"""Verify the aspiration variant runtime: legality, reliability, work, and moves.

Run inside the runtime's own module namespace by inserting the runtime dir on
sys.path first (runtimes share module names, so never import two together):

    python verify_aspir_variant.py <runtime_dir> <out_json>

Records per-position fixed-depth search results for the aspiration search and
the untouched ordered baseline living in the same runtime, legality of every
returned move, low-clock get_move reliability over sequential positions, and a
sequential self-play line exercising history reconstruction. This file never
claims strength; it gates freezing on mechanism engagement and safety.
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
from aspir_search import search as aspir_search  # noqa: E402
from ordered_search import search as plain_search  # noqa: E402

import agent  # noqa: E402

SUITE = Path(__file__).resolve().parent / "probe_suite_01.json"


def load_positions() -> list[dict]:
    data = json.loads(SUITE.read_text(encoding="utf-8-sig"))
    positions = data["positions"] if isinstance(data, dict) else data
    # Deterministic spread over the suite; categories overlap by design.
    return positions[:: 8][:30]


def main() -> None:
    warm_start = time.perf_counter()
    aspir_search(chess.Board(), seconds=0.0, soft_seconds=0.0, max_depth=1,
                 prior_keys=())
    warm_s = time.perf_counter() - warm_start

    rows = []
    for entry in load_positions():
        board = chess.Board(entry["fen"])
        result = aspir_search(board, seconds=30.0, soft_seconds=30.0,
                              max_depth=5, prior_keys=())
        move = chess.Move.from_uci(result["move"])
        assert move in board.legal_moves, (entry.get("id"), result["move"])
        assert not result["aborted"]
        reference = plain_search(board, seconds=30.0, soft_seconds=30.0,
                                 max_depth=5, prior_keys=())
        assert chess.Move.from_uci(reference["move"]) in board.legal_moves
        rows.append({
            "id": entry.get("id"),
            "fen": entry["fen"],
            "move": result["move"],
            "score": result["score"],
            "nodes": result["nodes"],
            "re_searches": result["aspiration_re_searches"],
            "baseline_move": reference["move"],
            "baseline_nodes": reference["nodes"],
        })

    # Low-clock reliability: one get_move per distinct position at 250ms.
    low_clock_failures = []
    for entry in load_positions()[:20]:
        board = chess.Board(entry["fen"])
        try:
            proposed = chess.Move.from_uci(agent.get_move(entry["fen"], 250))
            if proposed not in board.legal_moves:
                low_clock_failures.append(entry.get("id"))
        except Exception as error:
            low_clock_failures.append(f"{entry.get('id')}: {error!r}")

    # Sequential self-play line exercising history reconstruction and resets.
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
        "warmup_s": warm_s,
        "fixed_depth_rows": rows,
        "low_clock_failures": low_clock_failures,
        "selfplay_line": line_moves,
        "selfplay_legal": all(not m.startswith("ILLEGAL") for m in line_moves),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    # Mechanism must actually engage somewhere in the suite.
    total_re_searches = sum(r["re_searches"] for r in rows)
    payload["total_re_searches"] = total_re_searches
    disagreements = [r for r in rows if r["move"] != r["baseline_move"]]
    payload["disagreements"] = [
        {"id": r["id"], "aspir_move": r["move"],
         "baseline_move": r["baseline_move"], "aspir_score": r["score"],
         "baseline_score": r["baseline_score"],
         "delta_cp": (r["score"] - r["baseline_score"])}
        for r in disagreements
    ]
    worst = min((d["delta_cp"] for d in payload["disagreements"]), default=0)
    payload["worst_disagreement_delta_cp"] = worst
    # Aspiration scores are exact at the same fixed depth, so a large negative
    # swing on a changed decision signals a tactical defect, not noise.
    assert total_re_searches > 0, "aspiration never engaged; mechanism inert"
    assert worst >= -300, f"tactical defect: worst changed decision {worst}cp"
    payload["verified"] = (
        not low_clock_failures and payload["selfplay_legal"] and worst >= -300
    )
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"verified {RUNTIME.name}: rows={len(rows)} "
          f"re_searches={total_re_searches} disagreements={len(disagreements)} "
          f"worst_delta={worst}cp "
          f"low_clock_failures={len(low_clock_failures)} "
          f"selfplay_legal={payload['selfplay_legal']}")


if __name__ == "__main__":
    main()