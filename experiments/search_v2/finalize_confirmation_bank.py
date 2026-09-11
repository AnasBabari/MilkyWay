"""Freeze fresh openings only after checking the completed development record."""
from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import sys
from pathlib import Path

import chess
import chess.pgn

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.search_v2.build_confirmation_exclusions import board_digest  # noqa: E402
from tools.audit_recorded_screen import audit  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    direct = HERE / "direct_staged_vs_lmr_12s_50g"
    assert (direct / "report_50.json").exists(), "Wait for completed tiebreak"
    direct_audit = audit(direct)
    assert direct_audit["game_count"] == 50
    source = HERE / "confirmation_bank_01.json"
    output = HERE / "confirmation_bank_01_frozen.json"
    report_path = HERE / "confirmation_bank_final_audit_01.json"
    assert not output.exists() and not report_path.exists()
    bank = json.loads(source.read_text())
    index = HERE / "confirmation_exclusions_01.sqlite"
    metadata = json.loads(index.with_suffix(".json").read_text())
    assert digest(index) == metadata["index_sha256"] == bank["exclusion_index_sha256"]
    assert len(bank["positions"]) == 50 and bank["candidate_evaluation_used"] is False
    source_map = {row["path"]: row["sha256"] for row in metadata["sources"]}
    for name, expected in source_map.items():
        assert digest(ROOT / name) == expected, (name, "Indexed source changed")
    keys: set[bytes] = set()
    with sqlite3.connect(f"file:{index.as_posix()}?mode=ro", uri=True) as db:
        for row in bank["positions"]:
            board = chess.Board()
            for move in row["source_moves"]:
                assert chess.Move.from_uci(move) in board.legal_moves
                board.push_uci(move)
            assert board.fen() == row["fen"]
            assert board.is_valid() and not board.is_game_over() and not board.is_check()
            assert abs(row["white_score_cp"]) <= 50
            for key in (board_digest(board), board_digest(board.mirror())):
                assert key not in keys, "Duplicate or reflected opening"
                assert not db.execute("SELECT 1 FROM positions WHERE digest=?", (key,)).fetchone()
                keys.add(key)
    checked_new = []
    paths = set((ROOT / "experiments").glob("**/games/*.json"))
    paths.update((ROOT / "training/datasets").glob("**/game_*.json"))
    for path in sorted(paths):
        relative = str(path.relative_to(ROOT))
        if relative in source_map:
            continue
        record = json.loads(path.read_text())
        if not record.get("pgn"):
            # A new trajectory in an unknown schema must be explicitly reviewed.
            raise AssertionError((path, "New trajectory lacks replayable PGN"))
        game = chess.pgn.read_game(io.StringIO(record["pgn"]))
        assert game is not None and not game.errors
        board = game.board()
        assert board_digest(board) not in keys
        for move in game.mainline_moves():
            assert move in board.legal_moves
            board.push(move)
            assert board_digest(board) not in keys, (path, "Newly exposed bank position")
        checked_new.append({"path": relative, "sha256": digest(path)})
    report = {"status": "passed", "positions": 50, "legal_trajectories": True,
              "exact_and_reflected_training_overlap": 0,
              "indexed_source_hashes_verified": len(source_map),
              "post_snapshot_games_checked": checked_new,
              "tiebreak_audit": direct_audit, "bank_source_sha256": digest(source),
              "index_sha256": digest(index),
              "limitations": "Independence from recorded training/development inputs, not a "
              "claim that these chess positions have never appeared elsewhere."}
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    bank["status"] = "frozen independent bank"
    bank["final_audit_sha256"] = digest(report_path)
    bank["final_audit_path"] = str(report_path.relative_to(ROOT))
    output.write_text(json.dumps(bank, indent=2) + "\n")
    print(json.dumps({"bank": str(output), "positions": 50,
                      "new_games_audited": len(checked_new), "sha256": digest(output)}))


if __name__ == "__main__":
    main()
