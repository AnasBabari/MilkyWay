"""Middlegame blunder corpus: oracle-compare OUR moves (plies 20-80) in losses.

Games: silky-screen losses (combined + NMP, 12s) + full-clock live losses.
100k nodes/move, records loss_cp >= 60. Bounded (~350 analyses).
 Rule: diagnostic only; Stockfish never ships.
"""
import json
import sys
from pathlib import Path

import chess
import chess.engine

ROOT = Path("C:/Users/Babar/Documents/Coding/Projects/chess_bot/MilkyWay")
sys.path.insert(0, str(ROOT))
from baselines.stockfish.agent import find_stockfish_binary  # noqa: E402

OUT_DIR = ROOT / "experiments/middlegame_revision"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "middlegame_blunders.jsonl"
NODES = 100000
MIN_LOSS = 60


def our_losses(games_dir, limit):
    found = []
    for f in sorted(Path(games_dir).glob("*.json")):
        dat = json.loads(f.read_text())
        res, col = dat["result"], dat["candidate_color"]
        if res == "draw" or res == col or res == "void":
            continue
        found.append((f, dat))
        if len(found) >= limit:
            break
    return found


def main() -> None:
    targets = [
        (ROOT / "experiments/search_v2/combined_live_12s_50g/games", 5),
        (ROOT / "experiments/nmp_revision/nmp_vs_silky_12s_50g/games", 4),
        (ROOT / "experiments/search_v2/combined_live_120s_20g/games", 8),
    ]
    binary = find_stockfish_binary()
    assert binary
    n = 0
    with chess.engine.SimpleEngine.popen_uci(binary) as engine:
        engine.configure({"Threads": 1, "Hash": 64})
        for gdir, limit in targets:
            for path, dat in our_losses(gdir, limit):
                cand_white = dat["candidate_color"] == "white"
                mover = chess.WHITE if cand_white else chess.BLACK
                board = chess.Board(dat["start_fen"])
                import re

                pgn = dat["pgn"]
                body = pgn.split("\n\n", 1)[1]
                clean = re.sub(r"\{[^}]*\}|\d+\.+|1-0|0-1|1/2-1/2|\*", " ", body).split()
                for i, tok in enumerate(clean):
                    try:
                        mv = board.parse_san(tok)
                    except ValueError:
                        break
                    ply = i + 1
                    if board.turn == mover and 20 <= ply <= 80:
                        info0 = engine.analyse(board, chess.engine.Limit(nodes=NODES))
                        s0 = info0["score"].pov(mover)
                        b0 = s0.score(mate_score=100000)
                        board.push(mv)
                        info1 = engine.analyse(board, chess.engine.Limit(nodes=NODES))
                        s1 = info1["score"].pov(mover)
                        b1 = s1.score(mate_score=100000)
                        if b0 is not None and b1 is not None and b0 - b1 >= MIN_LOSS:
                            rec = {"game": f"{gdir.name}/{path.name}", "ply": ply,
                                   "played": mv.uci(), "loss_cp": b0 - b1,
                                   "before": b0, "after": b1}
                            with OUT.open("a") as fh:
                                fh.write(json.dumps(rec) + "\n")
                            n += 1
                    else:
                        board.push(mv)
    print(f"recorded {n} blunders -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
