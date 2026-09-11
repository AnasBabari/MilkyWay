"""Offline engine diagnosis of changed LMR decisions; never a runtime dependency."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import chess
import chess.engine

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from baselines.stockfish.agent import find_stockfish_binary  # noqa: E402


def main() -> None:
    out = HERE / "lmr_changed_moves_oracle_01.json"
    assert not out.exists()
    binary = find_stockfish_binary()
    assert binary is not None
    positions = json.loads((HERE / "probe_suite_01.json").read_text())["positions"]
    suite = {r["id"]: r for r in positions}
    rows = [json.loads(line) for line in
            (HERE / "lmr_probe_01/positions.jsonl").read_text().splitlines()]
    changed = [r for r in rows if r["results"]["disabled"]["move"]
               != r["results"]["lmr"]["move"]]
    results = []
    with chess.engine.SimpleEngine.popen_uci(binary) as engine:
        engine.configure({"Threads": 1, "Hash": 16, "Skill Level": 20})
        for row in changed:
            position = suite[row["id"]]
            board = chess.Board(position["history_start_fen"])
            for move in position["history_uci"]:
                board.push_uci(move)
            estimates = {}
            for arm in ("disabled", "lmr"):
                move = chess.Move.from_uci(row["results"][arm]["move"])
                engine.configure({"Clear Hash": None})
                info = engine.analyse(board, chess.engine.Limit(nodes=100000),
                                      root_moves=[move])
                estimates[arm] = {"move": move.uci(),
                                  "score_cp": info["score"].pov(board.turn).score(mate_score=30000),
                                  "nodes": info.get("nodes"), "depth": info.get("depth")}
            delta = estimates["lmr"]["score_cp"] - estimates["disabled"]["score_cp"]
            results.append({"id": row["id"], "estimates": estimates,
                            "lmr_minus_parent_cp": delta})
    result = {"purpose": "bounded offline diagnosis, not training or strength qualification",
              "stockfish_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
              "settings": {"skill": 20, "threads": 1, "hash_mb": 16,
                           "nodes_per_forced_move": 100000},
              "positions": results,
              "large_negative_deltas": sum(r["lmr_minus_parent_cp"] < -100 for r in results),
              "large_positive_deltas": sum(r["lmr_minus_parent_cp"] > 100 for r in results)}
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "positions"}), flush=True)


if __name__ == "__main__":
    main()
