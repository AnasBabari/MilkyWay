"""Read-only audit of recorded screen games, runtime hashes and clock comments."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

import chess
import chess.pgn


def audit(run: Path) -> dict[str, Any]:
    manifest = json.loads((run / "manifest.json").read_text())
    repository = Path(__file__).resolve().parents[1]
    for field in ("harness_sha256", "orchestration_sha256"):
        for name, digest in manifest[field].items():
            assert hashlib.sha256((repository / name).read_bytes()).hexdigest() == digest, name
    for role in ("agent", "opponent"):
        root = Path(manifest[role])
        for name, digest in manifest[f"{role}_sha256"].items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, (role, name)
    outcomes: Counter[str] = Counter()
    terminations: Counter[str] = Counter()
    games = []
    base, increment = manifest["base_ms"] / 1000, manifest["increment_ms"] / 1000
    positions = {p["id"]: p["fen"] for p in manifest["positions"]}
    for path in sorted((run / "games").glob("*.json")):
        raw = path.read_bytes()
        record = json.loads(raw)
        position_id = path.stem.rsplit("_", 1)[0]
        assert record["start_fen"] == positions[position_id]
        game = chess.pgn.read_game(io.StringIO(record["pgn"]))
        assert game is not None and not game.errors, path
        board = game.board()
        assert board.fen() == chess.Board(record["start_fen"]).fen()
        previous = {chess.WHITE: base, chess.BLACK: base}
        candidate = record["candidate_color"] == "white"
        spent = []
        clocks = []
        for node in game.mainline():
            assert node.move in board.legal_moves, path
            color = board.turn
            clock = node.clock()
            assert clock is not None, path
            used = previous[color] + increment - clock
            # PGN clock comments round to milliseconds.
            assert used >= -0.003 and clock >= -0.003, (path, used, clock)
            assert used <= previous[color] + 0.003, (path, used, previous[color])
            if color == candidate:
                spent.append(max(0.0, used))
                clocks.append(clock)
            previous[color] = clock
            board.push(node.move)
        result, term = record["result"], record["termination"]
        expected = {"white": "1-0", "black": "0-1", "draw": "1/2-1/2"}
        assert result in expected and game.headers["Result"] == expected[result], path
        if term == "checkmate":
            assert board.is_checkmate()
            assert result == ("black" if board.turn else "white")
        elif term == "threefold_repetition":
            assert board.is_repetition(3) and result == "draw"
        elif term == "fifty_moves":
            assert board.is_fifty_moves() and result == "draw"
        elif term == "insufficient_material":
            assert board.is_insufficient_material() and result == "draw"
        elif term == "stalemate":
            assert board.is_stalemate() and result == "draw"
        elif term == "ply_cap":
            assert board.ply() >= 600 and result == "draw"
        else:
            raise AssertionError((path, "Unreviewed/failed termination", term))
        outcome = "draw" if result == "draw" else (
            "win" if result == record["candidate_color"] else "loss")
        outcomes[outcome] += 1
        terminations[term] += 1
        games.append({"file": path.name, "outcome": outcome, "position_id": position_id,
                      "color": record["candidate_color"], "termination": term,
                      "moves": len(spent), "max_move_s": max(spent, default=0),
                      "min_remaining_s": min(clocks, default=base),
                      "sha256": hashlib.sha256(raw).hexdigest()})
    paired: Counter[str] = Counter()
    for position_id in {g["position_id"] for g in games}:
        pair = [g for g in games if g["position_id"] == position_id]
        assert len(pair) <= 2
        if len(pair) == 2:
            assert {g["color"] for g in pair} == {"white", "black"}
            paired.update(g["outcome"] for g in pair)
    n = len(games)
    return {"run": str(run.resolve()), "snapshot_only": True,
            "base_ms": manifest["base_ms"], "increment_ms": manifest["increment_ms"],
            "runtime_hashes_match": True, "game_count": n, "all_recorded_wdl": dict(outcomes),
            "harness_orchestration_hashes_match": True,
            "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "all_recorded_score": (outcomes["win"] + 0.5 * outcomes["draw"]) / n if n else None,
            "all_recorded_win_rate": outcomes["win"] / n if n else None,
            "complete_pairs_wdl": dict(paired), "terminations": dict(terminations), "games": games}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    reports = [audit(run) for run in args.runs]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(reports, indent=2))
    for report in reports:
        print(json.dumps({k: v for k, v in report.items() if k not in ("games", "terminations")}))


if __name__ == "__main__":
    main()
