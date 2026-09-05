"""Splits labeled chess positions into train, validation, and test sets.

Strict leakage prevention:
- Partitions by source_game_id (all positions from the same game remain in the same split)
- Fixed reproducible random seed
- Extracts 50-dimensional feature vectors and fixed terms
- Outputs both JSONL splits and compressed NPZ arrays
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import chess
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.scripts.extract_features import extract_features_white  # noqa: E402


def split_and_extract(
    input_file: Path,
    output_dir: Path,
    seed: int = 42,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    exclude_mates: bool = True,
) -> dict[str, int]:
    # Group records by source_game_id
    games: dict[str, list[dict[str, Any]]] = {}
    with input_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if exclude_mates and rec.get("is_mate", False):
                continue
            gid = rec.get("source_game_id", rec.get("position_id", "unknown"))
            games.setdefault(gid, []).append(rec)

    game_ids = sorted(games.keys())
    rng = random.Random(seed)
    rng.shuffle(game_ids)

    n_games = len(game_ids)
    n_train = int(n_games * train_ratio)
    n_val = int(n_games * val_ratio)

    train_games = set(game_ids[:n_train])
    val_games = set(game_ids[n_train : n_train + n_val])

    splits: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    for gid, recs in games.items():
        if gid in train_games:
            splits["train"].extend(recs)
        elif gid in val_games:
            splits["val"].extend(recs)
        else:
            splits["test"].extend(recs)

    output_dir.mkdir(parents=True, exist_ok=True)

    npz_data: dict[str, Any] = {}
    counts: dict[str, int] = {}

    for sname, rec_list in splits.items():
        counts[sname] = len(rec_list)
        # Write JSONL
        jsonl_path = output_dir / f"{sname}.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as out:
            for r in rec_list:
                out.write(json.dumps(r) + "\n")

        # Extract features into numpy
        X_list: list[list[float]] = []
        y_list: list[float] = []
        fixed_list: list[float] = []

        for r in rec_list:
            board = chess.Board(r["fen"])
            feats, fixed = extract_features_white(board)
            X_list.append(feats)
            fixed_list.append(fixed)
            y_list.append(float(r["sf_cp_white"]))

        npz_data[f"X_{sname}"] = np.array(X_list, dtype=np.float32)
        npz_data[f"y_{sname}"] = np.array(y_list, dtype=np.float32)
        npz_data[f"fixed_{sname}"] = np.array(fixed_list, dtype=np.float32)

    np.savez_compressed(output_dir / "dataset.npz", **npz_data)
    return counts


def get_default_input_path() -> Path:
    p25 = Path("training/datasets/labels/labels_25k.jsonl")
    if p25.is_file():
        return p25
    p1 = Path("training/datasets/labels/labels_1k.jsonl")
    if p1.is_file():
        return p1
    return p25


def main() -> None:
    parser = argparse.ArgumentParser(description="Split dataset into train/val/test.")
    parser.add_argument(
        "--input",
        type=Path,
        default=get_default_input_path(),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("training/datasets/processed"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    counts = split_and_extract(
        input_file=args.input,
        output_dir=args.output_dir,
        seed=args.seed,
    )
    print(f"Split complete: train={counts['train']}, val={counts['val']}, test={counts['test']}")


if __name__ == "__main__":
    main()
