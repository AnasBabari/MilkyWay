"""Offline full-strength oracle review of one retained game, for diagnosis only."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

import chess
import chess.engine
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from baselines.stockfish.agent import find_stockfish_binary  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--nodes", type=int, default=50000)
    parser.add_argument("--plies", type=int, nargs="*")
    parser.add_argument("--base-ms", type=int,
                        help="Initial clock; otherwise read the adjacent run manifest")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Use a new analysis output")
    base_ms = args.base_ms
    if base_ms is None:
        for parent in (args.game.parent, args.game.parent.parent):
            manifest_path = parent / "manifest.json"
            if manifest_path.exists():
                base_ms = json.loads(manifest_path.read_text()).get("base_ms")
                if base_ms is not None:
                    break
    if base_ms is None:
        parser.error("Supply --base-ms when no adjacent run manifest records the clock")
    record = json.loads(args.game.read_text())
    game = chess.pgn.read_game(io.StringIO(record["pgn"]))
    assert game is not None and not game.errors
    binary = find_stockfish_binary()
    assert binary
    rows = []
    with chess.engine.SimpleEngine.popen_uci(binary) as oracle:
        oracle.configure({"Threads": 1, "Hash": 32, "Skill Level": 20})
        board = game.board()
        previous_clock = {chess.WHITE: base_ms / 1000, chess.BLACK: base_ms / 1000}
        for node in game.mainline():
            move = node.move
            assert move in board.legal_moves
            color = "white" if board.turn else "black"
            if color == record["candidate_color"] and (
                args.plies is None or board.ply() in args.plies
            ):
                best = oracle.analyse(board, chess.engine.Limit(nodes=args.nodes), game=object())
                played = oracle.analyse(board, chess.engine.Limit(nodes=args.nodes),
                                        root_moves=[move], game=object())
                best_cp = best["score"].pov(board.turn).score(mate_score=10000)
                played_cp = played["score"].pov(board.turn).score(mate_score=10000)
                row = {"ply": board.ply(), "fen": board.fen(), "move": move.uci(),
                       "san": board.san(move), "best": best["pv"][0].uci(),
                       "best_cp": best_cp, "played_cp": played_cp,
                       "loss_cp": (0 if best["pv"][0] == move else max(0, best_cp - played_cp)),
                       "clock_before_s": previous_clock[board.turn],
                       "clock_after_s": node.clock()}
                rows.append(row)
                if row["loss_cp"] >= 150:
                    print(json.dumps(row), flush=True)
            previous_clock[board.turn] = node.clock()
            board.push(move)
    report = {"game_sha256": hashlib.sha256(args.game.read_bytes()).hexdigest(),
              "stockfish_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
              "nodes_per_analysis": args.nodes, "skill": 20, "threads": 1, "hash_mb": 32,
              "purpose": "offline diagnostic; estimates depend on bounded search, not ground truth",
              "initial_clock_ms": base_ms,
              "moves": rows}
    args.out.write_text(json.dumps(report, indent=2))
    print(f"Saved {len(rows)} candidate moves")


if __name__ == "__main__":
    main()
