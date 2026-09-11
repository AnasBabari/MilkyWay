"""Convert referee self-play into game-split white-perspective outcome targets."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import io
import json
import sys
from pathlib import Path

import chess.pgn
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if (args.games / "writer.lock").exists():
        raise SystemExit("Wait for self-play to finish before freezing the outcome dataset")
    if args.out.exists():
        raise SystemExit("Refusing to overwrite a dataset")
    sys.path.insert(0, str(ROOT / "experiments/silky_snow"))
    evaluation = importlib.import_module("evaluation")
    representation = importlib.import_module("root_policy")
    records = {"train": [], "val": []}
    game_ids = {"train": [], "val": []}
    hashes = {}
    terminations = {}
    for path in sorted(args.games.glob("game_*.json")):
        record = json.loads(path.read_text())
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        result = record["result"]
        assert result in ("white", "black", "draw")
        outcome = {"white": 1.0, "black": 0.0, "draw": 0.5}[result]
        game = chess.pgn.read_game(io.StringIO(record["pgn"]))
        assert game is not None and not game.errors
        expected = {"white": "1-0", "black": "0-1", "draw": "1/2-1/2"}[result]
        assert game.headers["Result"] == expected
        split = record["split"]
        game_ids[split].append(record["game_id"])
        board = game.board()
        assert board.fen() == record["start_fen"]
        assert board.is_valid()
        assert record["game_id"] not in game_ids[split][:-1], "Duplicate game ID"
        term = record["termination"]
        assert game.headers["Termination"] == term
        terminations[term] = terminations.get(term, 0) + 1
        for move in game.mainline_moves():
            assert move in board.legal_moves
            x = representation.board_to_tensor(board)[:12].reshape(768)
            anchor = float(evaluation.evaluate(board)) * (1 if board.turn else -1)
            records[split].append((x, anchor, outcome))
            board.push(move)
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
        else:
            raise ValueError(f"Unreviewed termination {term}: {path}")
    assert set(game_ids["train"]).isdisjoint(game_ids["val"])
    assert len(game_ids["train"]) >= 8 and len(game_ids["val"]) >= 2
    args.out.mkdir(parents=True)
    for split, rows in records.items():
        np.savez_compressed(args.out / f"{split}.npz",
                            x=np.asarray([r[0] for r in rows], np.uint8),
                            anchor=np.asarray([r[1] for r in rows], np.float32),
                            target=np.asarray([r[2] for r in rows], np.float32))
    manifest = {"games": game_ids, "sources": hashes,
                "terminations": terminations,
                "converter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "positions": {s: len(r) for s, r in records.items()},
                "learning": "Monte Carlo outcome value learning; not policy gradient",
                "limits": "small initial batch; validation is diagnostic, not promotion evidence"}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest["positions"]))


if __name__ == "__main__":
    main()
