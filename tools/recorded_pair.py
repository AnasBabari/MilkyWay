"""Paired games retaining raw referee PGNs without modifying the referee."""
from __future__ import annotations

import json
from pathlib import Path

import chess

from harness.referee import FAILED_TERMINATIONS, play_match
from harness.sandbox import local
from tools.m18_tournament import PairRecord
from tools.test_bank import BankPosition


def play_recorded_pair(
    agent_dir: Path, opponent_dir: Path, pos: BankPosition,
    base_ms: int, increment_ms: int, out: Path,
) -> PairRecord:
    """Use exactly the existing pair clocks and default per-agent seed.

    Caller owns the single writer lock and freezes code/protocol hashes.
    Existing complete game records may be reused only under that manifest.
    """
    out.mkdir(parents=True, exist_ok=True)
    games = []
    scores = []
    for color in ("white", "black"):
        path = out / f"{pos.id}_{color}.json"
        if path.exists():
            record = json.loads(path.read_text())
            assert record["start_fen"] == pos.fen and record["candidate_color"] == color
        else:
            white, black = ((agent_dir, opponent_dir) if color == "white"
                            else (opponent_dir, agent_dir))
            result = play_match(local(white), local(black), base_ms, increment_ms,
                                start_fen=pos.fen)
            record = {"start_fen": pos.fen, "candidate_color": color,
                      "result": result.result, "termination": result.termination,
                      "pgn": result.pgn}
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(record, indent=2))
            tmp.replace(path)
        # Preserve the failed game before rejecting it; never silently score a void as a draw.
        if record["result"] == "void" or record["termination"] in FAILED_TERMINATIONS:
            raise RuntimeError(f"Reliability failure saved at {path}: {record['termination']}")
        assert record["result"] in ("white", "black", "draw")
        scores.append(0.5 if record["result"] == "draw" else float(record["result"] == color))
        games.append(record)
    return PairRecord(pos.id, pos.category, pos.fen, chess.Board(pos.fen).ply(),
                      games[0]["result"], games[0]["termination"], scores[0],
                      games[1]["result"], games[1]["termination"], scores[1], sum(scores))
