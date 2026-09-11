"""Curate the firesock middlegame dataset (deterministic).

Sources: 12 GM PGNs (human middlegame theory, game-outcome targets) +
64 SF7 self-play games (engine truth). Keeps positions with
16 <= ply <= 90 AND (queens >= 1 OR rooks >= 2). Uniform per-game cap.
Game-split isolation (GM by hash; SF7 by the published split manifest).
Emits train.npz/val.npz with x/anchor/target + manifest.json, matching
the compact outcome trainer's expected format exactly.
"""

from __future__ import annotations

import importlib
import io
import json
import sys
from pathlib import Path

import chess
import chess.pgn
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/silky_snow"))
evaluation = importlib.import_module("evaluation")
representation = importlib.import_module("root_policy")

PGN_DIR = ROOT / "training/data/raw_pgn"
GM_FILES = ["Anand", "Aronian", "Carlsen", "Caruana", "Ding", "Fischer",
            "Karpov", "Kasparov", "Kramnik", "Nakamura", "Nepomniachtchi", "Topalov"]
SF7_GAMES = ROOT / "training/datasets/compact_sf7_fullclock_01"
SF7_MANIFEST = ROOT / "training/datasets/compact_sf7_fullclock_outcomes_01/manifest.json"
OUT = ROOT / "training/datasets/compact_firesock_midgame_01"

MIN_PLY = 16
MAX_PLY = 90
PER_GAME_CAP = 12
VAL_EVERY = 7  # game hash mod 7 == 0 -> validation (~1/7)


def is_midgame(board: chess.Board) -> bool:
    ply = board.ply()
    if not MIN_PLY <= ply <= MAX_PLY:
        return False
    queens = rooks = 0
    for piece in board.piece_map().values():
        if piece.piece_type == chess.QUEEN:
            queens += 1
        elif piece.piece_type == chess.ROOK:
            rooks += 1
    return queens >= 1 or rooks >= 2


def featurize(board: chess.Board, outcome: float) -> tuple:
    x = representation.board_to_tensor(board)[:12].reshape(768)
    anchor = float(evaluation.evaluate(board)) * (1 if board.turn else -1)
    return (x, anchor, outcome)


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite {OUT}")
    OUT.mkdir(parents=True)
    records: dict[str, list] = {"train": [], "val": []}
    game_ids: dict[str, list] = {"train": [], "val": []}
    game_n = 0

    # 1. GM games (hash split)
    for name in GM_FILES:
        path = PGN_DIR / (name + ".pgn")
        with path.open(encoding="utf-8", errors="replace") as fh:
            while True:
                game = chess.pgn.read_game(fh)
                if game is None:
                    break
                res = game.headers.get("Result", "*")
                if res not in ("1-0", "0-1", "1/2-1/2"):
                    continue
                outcome = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[res]
                game_n += 1
                split = "val" if game_n % VAL_EVERY == 0 else "train"
                game_ids[split].append(f"gm:{name}:{game_n}")
                board = game.board()
                kept = []
                for move in game.mainline_moves():
                    if is_midgame(board):
                        kept.append(featurize(board, outcome))
                    if board.is_game_over():
                        break
                    board.push(move)
                stride = max(1, (len(kept) + PER_GAME_CAP - 1) // PER_GAME_CAP)
                records[split].extend(kept[::stride][:PER_GAME_CAP])
        print(f"{name}: cumulative GM games={game_n}", flush=True)

    # 2. SF7 games (published splits)
    sf_manifest = json.loads(SF7_MANIFEST.read_text())
    sf_split = {}
    for split in ("train", "val"):
        for gid in sf_manifest["games"][split]:
            sf_split[str(gid)] = split
    sf_n = 0
    for path in sorted(SF7_GAMES.glob("game_*.json")):
        record = json.loads(path.read_text())
        gid = str(record["game_id"])
        if gid not in sf_split:
            continue
        split = sf_split[gid]
        outcome = {"white": 1.0, "black": 0.0, "draw": 0.5}[record["result"]]
        game = chess.pgn.read_game(io.StringIO(record["pgn"]))
        assert game is not None and not game.errors
        game_ids[split].append(f"sf7:{gid}")
        sf_n += 1
        board = game.board()
        kept = []
        for move in game.mainline_moves():
            if is_midgame(board):
                kept.append(featurize(board, outcome))
            board.push(move)
        stride = max(1, (len(kept) + PER_GAME_CAP - 1) // PER_GAME_CAP)
        records[split].extend(kept[::stride][:PER_GAME_CAP])
    print(f"SF7 games used: {sf_n}", flush=True)

    sources = []
    for split in ("train", "val"):
        xs = np.array([r[0] for r in records[split]], dtype=np.uint8)
        anchors = np.array([r[1] for r in records[split]], dtype=np.float32)
        targets = np.array([r[2] for r in records[split]], dtype=np.float32)
        np.savez(OUT / f"{split}.npz", x=xs, anchor=anchors, target=targets)
        sources.append({split: len(xs)})
    manifest = {"spec": "middlegame 16<=ply<=90 and (queens>=1 or rooks>=2); "
                "cap 12/game uniform stride; GM hash-split 6/7, SF7 published splits",
                "counts": sources, "game_ids": {k: len(v) for k, v in game_ids.items()},
                "gm_games": game_n, "sf7_games": sf_n}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
