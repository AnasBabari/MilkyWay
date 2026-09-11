# ruff: noqa: E402
"""Build balanced master-game shards without benchmark or cross-split leakage.

Decisive games and winning-side moves are a quality heuristic, not measured accuracy.
No self-play or benchmark positions are substituted when input PGNs are exhausted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import chess.pgn

from tools.confirm_bank import CONFIRM_TEST_BANK
from tools.measure_acpl import ACPL_TEST_SUITE, ACPLPosition
from tools.screen_bank import SCREEN_TEST_BANK
from tools.test_bank import PAIRED_TEST_BANK, BankPosition
from training.data.dataset import PositionRecord, split_game_id, write_shard_npz

SOURCES = ("Carlsen", "Kasparov", "Karpov", "Fischer")


def position_key(fen: str) -> str:
    """Ignore clocks; normalize en-passant in python-chess before comparing."""
    return " ".join(chess.Board(fen).fen().split()[:4])


def master_records(
    path: Path,
    excluded: set[str],
    seen_games: set[str],
) -> Iterator[PositionRecord]:
    with path.open(encoding="utf-8-sig", errors="replace") as source:
        while (game := chess.pgn.read_game(source)) is not None:
            if game.errors or game.headers.get("Variant", "Standard") != "Standard":
                continue
            result = game.headers.get("Result")
            if result not in ("1-0", "0-1"):
                continue
            moves = list(game.mainline_moves())
            identity = game.board().fen() + " " + " ".join(m.uci() for m in moves)
            game_id = hashlib.sha256(identity.encode()).hexdigest()
            if game_id in seen_games:
                continue
            seen_games.add(game_id)
            board = game.board()
            records: list[PositionRecord] = []
            held_out = False
            for ply, move in enumerate(moves, 1):
                if not board.is_valid() or move not in board.legal_moves:
                    held_out = True
                    break
                fen = board.fen()
                if position_key(fen) in excluded:
                    held_out = True
                winner = chess.WHITE if result == "1-0" else chess.BLACK
                if ply >= 12 and ply % 4 in (0, 1) and board.turn == winner:
                    records.append(
                        PositionRecord(
                            position_id=f"{game_id}_{ply}",
                            fen=fen,
                            source=path.stem,
                            source_game_id=game_id,
                            source_ply=ply,
                            side_to_move=int(board.turn),
                            played_move=move.uci(),
                            game_result=1.0 if result == "1-0" else 0.0,
                        )
                    )
                board.push(move)
            if not held_out:
                yield from records


def build_extended_dataset(
    pgn_dir: Path,
    output: Path,
    target: int,
    shard_size: int,
) -> dict[str, Any]:
    if target < 4 or shard_size < 1:
        raise ValueError("Target must be at least four and shard size positive")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use an empty output directory to avoid mixing datasets")
    files = [pgn_dir / f"{name}.pgn" for name in SOURCES]
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
    # Common book openings are excluded as records, but must not exclude every game.
    banks: list[ACPLPosition | BankPosition] = [
        *ACPL_TEST_SUITE, *SCREEN_TEST_BANK, *CONFIRM_TEST_BANK, *PAIRED_TEST_BANK,
    ]
    excluded = {position_key(p.fen) for p in banks}
    game_excluded = {position_key(p.fen) for p in banks if chess.Board(p.fen).ply() >= 12}
    seen_games: set[str] = set()
    seen_positions = set(excluded)
    generators = [master_records(p, game_excluded, seen_games) for p in files]
    output.mkdir(parents=True, exist_ok=True)
    buffers: dict[str, list[PositionRecord]] = {s: [] for s in ("train", "val", "test")}
    counts: Counter[str] = Counter()
    shards: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    metadata: list[dict[str, Any]] = []

    def flush(split: str) -> None:
        records = buffers[split]
        if not records:
            return
        directory = output / split
        directory.mkdir(exist_ok=True)
        path = directory / f"shard_{shards[split]:05d}.npz"
        write_shard_npz(records, path)
        raw = path.with_suffix(".jsonl")
        raw.write_text("".join(json.dumps(r.to_dict()) + "\n" for r in records))
        metadata.append(
            {
                "path": str(path.relative_to(output)),
                "count": len(records),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
        counts[split] += len(records)
        shards[split] += 1
        buffers[split] = []

    quotas = [target // 4 + int(i < target % 4) for i in range(4)]
    active = set(range(4))
    while active:
        for i in sorted(active):
            if source_counts[SOURCES[i]] >= quotas[i]:
                active.remove(i)
                continue
            while True:
                record = next(generators[i], None)
                if record is None:
                    active.remove(i)
                    break
                key = position_key(record.fen)
                if key in seen_positions:
                    continue
                seen_positions.add(key)
                split = split_game_id(record.source_game_id)
                buffers[split].append(record)
                source_counts[SOURCES[i]] += 1
                if len(buffers[split]) >= shard_size:
                    flush(split)
                break
    for split in buffers:
        flush(split)
    manifest = {
        "target_positions": target,
        "total_positions": sum(counts.values()),
        "complete": sum(counts.values()) == target,
        "source_counts": dict(source_counts),
        "split_counts": dict(counts),
        "quality_filter": "valid decisive standard games; winning-side sampled moves",
        "split_method": "SHA256 of initial FEN plus complete game moves",
        "excluded_position_count": len(excluded),
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        "shards": metadata,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-positions", type=int, default=100000)
    parser.add_argument("--shard-size", type=int, default=10000)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "training/datasets/master_extended_100k"
    )
    parser.add_argument("--pgn-dir", type=Path, default=ROOT / "training/data/raw_pgn")
    args = parser.parse_args()
    manifest = build_extended_dataset(
        args.pgn_dir,
        args.output_dir,
        args.target_positions,
        args.shard_size,
    )
    print(json.dumps(manifest, indent=2))
    if not manifest["complete"]:
        raise SystemExit("PGNs exhausted before balanced target; partial dataset recorded")


if __name__ == "__main__":
    main()
