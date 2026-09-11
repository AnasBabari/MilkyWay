"""Build a Polyglot opening book from OUR human game corpora (no engine games).

Sources: 12 GM PGNs (~55k games) + Lichess200k.pgn (7k, 2000+ Elo).
Weight (mover perspective): win=3, draw=1, loss=0. Entries need total
weight >= MIN_WEIGHT and come from plies <= MAX_PLY. Deterministic output
(sorted keys). Verifies by reading back every entry with chess.polyglot.
"""

import json
import struct
from collections import defaultdict
from pathlib import Path

import chess
import chess.pgn
import chess.polyglot

ROOT = Path("C:/Users/Babar/Documents/Coding/Projects/chess_bot/MilkyWay")
PGN_DIR = ROOT / "training/data/raw_pgn"
OUT = ROOT / "experiments/firesock_revision/firesock_book.bin"
REPORT = ROOT / "experiments/firesock_revision/book_build_report.json"

GM_FILES = ["Anand", "Aronian", "Carlsen", "Caruana", "Ding", "Fischer",
            "Karpov", "Kasparov", "Kramnik", "Nakamura", "Nepomniachtchi", "Topalov"]
LICHESS_FILES = ["Lichess200k"]
MAX_PLY = 30
MIN_WEIGHT = 4
MAX_WEIGHT = 60000

ENTRY = struct.Struct(">QHHI")


def encode_move(move: chess.Move) -> int:
    promo = 0 if move.promotion is None else move.promotion - 1
    return move.to_square | (move.from_square << 6) | (promo << 12)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    agg: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    games = draws = 0
    files = [PGN_DIR / (n + ".pgn") for n in GM_FILES + LICHESS_FILES]
    for path in files:
        if not path.is_file():
            print(f"MISSING {path}")
            continue
        with path.open(encoding="utf-8", errors="replace") as fh:
            while True:
                game = chess.pgn.read_game(fh)
                if game is None:
                    break
                res = game.headers.get("Result", "*")
                if res not in ("1-0", "0-1", "1/2-1/2"):
                    continue
                games += 1
                draws += res == "1/2-1/2"
                board = game.board()
                for ply, move in enumerate(game.mainline_moves()):
                    if ply >= MAX_PLY or board.is_game_over():
                        break
                    mover_white = board.turn == chess.WHITE
                    if res == "1/2-1/2":
                        w = 1
                    elif (res == "1-0") == mover_white:
                        w = 3
                    else:
                        w = 0
                    if w:
                        key = chess.polyglot.zobrist_hash(board)
                        agg[key][move.uci()] += w
                    board.push(move)
        print(f"parsed {path.name}: games={games}", flush=True)

    entries = []
    dropped = 0
    for key in sorted(agg):
        total = sum(agg[key].values())
        if total < MIN_WEIGHT:
            dropped += 1
            continue
        for uci, w in sorted(agg[key].items(), key=lambda kv: (-kv[1], kv[0])):
            move = chess.Move.from_uci(uci)
            entries.append((key, encode_move(move), min(w, MAX_WEIGHT), 0))
    with OUT.open("wb") as fh:
        for key, raw, weight, learn in entries:
            fh.write(ENTRY.pack(key, raw, weight, learn))
    print(f"entries={len(entries)} dropped={dropped} "
          f"size={OUT.stat().st_size}", flush=True)

    # full readback verification through the same reader the runtime uses
    reader = chess.polyglot.open_reader(str(OUT))
    checked = mismatch = 0
    for entry in reader:
        checked += 1
        if entry.move is None:
            mismatch += 1
    # legality + fidelity on a replayed sample is covered by coverage probe;
    # here assert structural roundtrip on every entry
    print(f"readback: {checked} entries decoded, null={mismatch}", flush=True)
    assert checked == len(entries) and mismatch == 0
    report = {"games": games, "draws": draws, "entries": len(entries),
              "dropped_positions": dropped, "bytes": OUT.stat().st_size,
              "max_ply": MAX_PLY, "min_weight": MIN_WEIGHT,
              "sha256": __import__("hashlib").sha256(OUT.read_bytes()).hexdigest()}
    REPORT.write_text(json.dumps(report, indent=1))
    print("OK", flush=True)


if __name__ == "__main__":
    main()
