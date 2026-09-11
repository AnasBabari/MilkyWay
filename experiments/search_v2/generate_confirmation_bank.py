"""Generate candidate-blind confirmation openings using offline Stockfish only."""
from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import sys
from pathlib import Path

import chess
import chess.engine

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from baselines.stockfish.agent import find_stockfish_binary  # noqa: E402
from experiments.search_v2.build_confirmation_exclusions import board_digest  # noqa: E402


def main() -> None:
    output = HERE / "confirmation_bank_01.json"
    partial = HERE / "confirmation_bank_generation_01.jsonl"
    assert not output.exists() and not partial.exists(), "Preserve existing generation evidence"
    protocol_path = HERE / "CONFIRMATION_BANK_PROTOCOL.json"
    protocol = json.loads(protocol_path.read_text())
    index = HERE / "confirmation_exclusions_01.sqlite"
    metadata = json.loads(index.with_suffix(".json").read_text())
    assert hashlib.sha256(index.read_bytes()).hexdigest() == metadata["index_sha256"]
    binary = find_stockfish_binary()
    assert binary is not None
    rng = random.Random(protocol["seed"])
    positions = []
    accepted_keys: set[bytes] = set()
    rejected: dict[str, int] = {}
    with (
        sqlite3.connect(f"file:{index.as_posix()}?mode=ro", uri=True) as db,
        chess.engine.SimpleEngine.popen_uci(binary) as engine,
    ):
        engine.configure({"Threads": 1, "Hash": 16, "Skill Level": 20})
        for attempt in range(1, 1001):
            board = chess.Board()
            moves = []
            requested_ply = rng.randint(*protocol["trajectory_plies"])
            for _ in range(requested_ply):
                if board.is_game_over():
                    break
                engine.configure({"Clear Hash": None})
                lines = engine.analyse(
                    board, chess.engine.Limit(nodes=protocol["trajectory_nodes_per_position"]),
                    multipv=protocol["multipv"],
                )
                # Stable UCI ordering before seeded selection; no candidate evaluation.
                choices = sorted({line["pv"][0] for line in lines}, key=lambda m: m.uci())
                move = rng.choice(choices)
                moves.append(move.uci())
                board.push(move)
            reason = None
            keys = (board_digest(board), board_digest(board.mirror()))
            if board.is_game_over() or board.is_check() or len(moves) != requested_ply:
                reason = "terminal_or_check"
            elif any(key in accepted_keys for key in keys):
                reason = "duplicate"
            elif any(db.execute("SELECT 1 FROM positions WHERE digest=?", (key,)).fetchone()
                     for key in keys):
                reason = "previously_exposed"
            score = None
            if reason is None:
                engine.configure({"Clear Hash": None})
                info = engine.analyse(
                    board, chess.engine.Limit(nodes=protocol["final_balance_nodes"])
                )
                score = info["score"].white().score(mate_score=30000)
                assert score is not None
                if abs(score) > protocol["maximum_absolute_white_score_cp"]:
                    reason = "unbalanced"
            record = {"attempt": attempt, "source_moves": moves, "fen": board.fen(),
                      "white_score_cp": score, "rejection": reason}
            with partial.open("a") as stream:
                stream.write(json.dumps(record) + "\n")
            if reason:
                rejected[reason] = rejected.get(reason, 0) + 1
                continue
            positions.append({"id": f"fresh_confirm_{len(positions) + 1:03d}",
                              "category": "opening", **record})
            accepted_keys.update(keys)
            print(f"Accepted {len(positions)}/{protocol['positions']} at attempt {attempt}",
                  flush=True)
            if len(positions) == protocol["positions"]:
                break
    assert len(positions) == protocol["positions"], "Insufficient openings; preserve attempts"
    result = {"status": "generated; final post-tiebreak overlap audit still required",
              "protocol": protocol, "positions": positions, "rejections": rejected,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
              "exclusion_index_sha256": metadata["index_sha256"],
              "stockfish_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
              "stockfish_options": {"Threads": 1, "Hash": 16, "Skill Level": 20},
              "candidate_evaluation_used": False,
              "generation_log_sha256": hashlib.sha256(partial.read_bytes()).hexdigest()}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Generated {len(positions)} fresh openings; not yet used in qualification.", flush=True)


if __name__ == "__main__":
    main()
