# ruff: noqa: E402
"""Build a value-grade position set: every game phase, both colours, all results.

Unlike the policy-oriented builder (winner moves from decisive games only),
this keeps positions from BOTH sides and draws, with game results as metadata
only. Stockfish scores are added by a separate labelling pass; the value
signal must come from search, never from filtering to winners.

Usage:
  training/.venv/Scripts/python.exe training/scripts/build_value_dataset.py \
      --target-positions 60000 --out training/datasets/master_value_v1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import chess.pgn

from tools.confirm_bank import CONFIRM_TEST_BANK
from tools.measure_acpl import ACPL_TEST_SUITE, ACPLPosition
from tools.screen_bank import SCREEN_TEST_BANK
from tools.test_bank import PAIRED_TEST_BANK, BankPosition

BankEntry = ACPLPosition | BankPosition
from training.data.dataset import PositionRecord, split_game_id

SOURCES = (
    "Carlsen", "Kasparov", "Karpov", "Fischer",
    "Anand", "Kramnik", "Nakamura", "Caruana",
    "Topalov", "Aronian", "Ding", "Nepomniachtchi",
)
EXTRA_GAMES = ("r44_imperialists", "r35_tempo")


def position_key(fen: str) -> str:
    return " ".join(chess.Board(fen).fen().split()[:4])


def game_records(
    game: chess.pgn.Game,
    source: str,
    game_id: str,
    result: float,
    excluded: set[str],
    max_per_game: int,
) -> Iterator[PositionRecord]:
    moves = list(game.mainline_moves())
    if len(moves) < 16:
        return
    board = game.board()
    kept = 0
    # Stride 2 plies from move 8: phases, both colours, bounded per game.
    for ply, move in enumerate(moves, 1):
        if not board.is_valid() or move not in board.legal_moves:
            return
        if ply >= 8 and ply % 2 == 0 and kept < max_per_game:
            fen = board.fen()
            if position_key(fen) not in excluded:
                yield PositionRecord(
                    position_id=f"{game_id}_{ply}",
                    fen=fen,
                    source=source,
                    source_game_id=game_id,
                    source_ply=ply,
                    side_to_move=int(board.turn),
                    played_move=move.uci(),
                    game_result=result,
                )
                kept += 1
        board.push(move)


def iter_pgn_records(
    path: Path, source: str, excluded: set[str], seen_games: set[str], max_per_game: int
) -> Iterator[PositionRecord]:
    with path.open(encoding="utf-8-sig", errors="replace") as handle:
        while (game := chess.pgn.read_game(handle)) is not None:
            if game.errors or game.headers.get("Variant", "Standard") != "Standard":
                continue
            result = game.headers.get("Result")
            if result == "1-0":
                score = 1.0
            elif result == "0-1":
                score = 0.0
            elif result == "1/2-1/2":
                score = 0.5
            else:
                continue
            moves = list(game.mainline_moves())
            identity = game.board().fen() + " " + " ".join(m.uci() for m in moves)
            game_id = hashlib.sha256(identity.encode()).hexdigest()
            if game_id in seen_games:
                continue
            seen_games.add(game_id)
            yield from game_records(game, source, game_id, score, excluded, max_per_game)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-positions", type=int, default=60000)
    parser.add_argument("--max-per-game", type=int, default=24)
    parser.add_argument(
        "--sources", type=str, default=",".join(SOURCES),
        help="Comma-separated PGN stems to ingest (default: all masters)",
    )
    parser.add_argument("--out", type=Path, default=ROOT / "training/datasets/master_value_v1")
    parser.add_argument("--pgn-dir", type=Path, default=ROOT / "training/data/raw_pgn")
    args = parser.parse_args()

    banks: list[BankEntry] = [
        *ACPL_TEST_SUITE, *SCREEN_TEST_BANK, *CONFIRM_TEST_BANK, *PAIRED_TEST_BANK,
    ]
    excluded = {position_key(p.fen) for p in banks}
    # Rated losses under study: keep as ordinary positions (no special weight).
    rated = list(Path("C:/Users/Babar/Downloads").glob("aichessathon-round-*.pgn"))

    out: Path = args.out
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to mix into non-empty {out}")
    out.mkdir(parents=True, exist_ok=True)

    seen_games: set[str] = set()
    seen_positions = set(excluded)
    counts: Counter[str] = Counter()
    buffers: dict[str, list[PositionRecord]] = {}
    total = 0

    def emit(split: str, rec: PositionRecord) -> None:
        buffers.setdefault(split, []).append(rec)

    # Quotas apply to the requested master sources only; short rated PGNs
    # append whatever they hold without consuming master quota.
    wanted = [s for s in args.sources.split(",") if s]
    sources: list[tuple[str, Path]] = [(s, args.pgn_dir / f"{s}.pgn") for s in wanted]
    sources += [(p.stem, p) for p in sorted(rated)]
    n_masters = len(wanted)
    quotas = [args.target_positions // n_masters] * len(sources)
    for i in range(args.target_positions % n_masters):
        quotas[i] += 1
    generators: list[Iterator[PositionRecord] | None] = []
    for source, path in sources:
        if not path.is_file():
            print(f"skip missing {path}")
            generators.append(None)
        else:
            generators.append(
                iter_pgn_records(path, source, excluded, seen_games, args.max_per_game)
            )
    active = {i for i, g in enumerate(generators) if g is not None}
    while active and total < args.target_positions:
        for i in sorted(active):
            gen = generators[i]
            assert gen is not None
            source = sources[i][0]
            if counts[source] >= quotas[i]:
                active.remove(i)
                continue
            while True:
                rec = next(gen, None)
                if rec is None:
                    active.remove(i)
                    break
                key = position_key(rec.fen)
                if key in seen_positions:
                    continue
                seen_positions.add(key)
                emit(split_game_id(rec.source_game_id), rec)
                counts[source] += 1
                total += 1
                break
    for split, records in buffers.items():
        with open(out / f"{split}.jsonl", "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec.to_dict()) + "\n")
    summary = {"total": total, "by_source": dict(counts), "excluded_bank": len(excluded)}
    (out / "records_manifest.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
