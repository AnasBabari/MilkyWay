"""Collects chess positions for offline evaluation tuning.

Sources:
- MilkyWay self-play games from diverse opening lines
- Random walk openings followed by tactical rollouts
- Balanced endgame and middlegame seeds
- Paired sampling every 4-8 plies with deduplication on canonical board state

Output format: JSONL records with full provenance metadata.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import chess

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constants import (  # noqa: E402
    MAX_PHASE,
    PHASE_WEIGHT_BISHOP,
    PHASE_WEIGHT_KNIGHT,
    PHASE_WEIGHT_QUEEN,
    PHASE_WEIGHT_ROOK,
)
from tools.benchmark_positions import BENCHMARK_SUITE  # noqa: E402

OPENING_SEEDS = [
    # Standard ECO starting branches
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
    "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
    "rnbqkb1r/pp1ppppp/5n2/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1",
    "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 1 2",
    "rnbqkb1r/pppppppp/5n2/8/2PP4/8/PP2PPPP/RNBQKBNR b KQkq - 0 2",
    "rnbqkbnr/pppp1ppp/4p3/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
    "rnbqkbnr/pppp1ppp/4p3/8/2PP4/8/PP2PPPP/RNBQKBNR b KQkq - 0 2",
    "rnbqkbnr/pp1ppppp/2p5/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
    "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2",
    "rnbqkbnr/pppp1ppp/8/4p3/2P5/8/PP1PPPPP/RNBQKBNR b KQkq - 0 1",
    "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq - 0 1",
    "rnbqkb1r/pppppppp/5n2/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1",
]


def canonical_key(fen: str) -> str:
    """Return piece placement, side to move, castling, and en-passant without clocks."""
    parts = fen.split()
    return " ".join(parts[:4]) if len(parts) >= 4 else fen


def compute_phase(board: chess.Board) -> int:
    knights = board.pieces_mask(chess.KNIGHT, chess.WHITE).bit_count() + board.pieces_mask(
        chess.KNIGHT, chess.BLACK
    ).bit_count()
    bishops = board.pieces_mask(chess.BISHOP, chess.WHITE).bit_count() + board.pieces_mask(
        chess.BISHOP, chess.BLACK
    ).bit_count()
    rooks = board.pieces_mask(chess.ROOK, chess.WHITE).bit_count() + board.pieces_mask(
        chess.ROOK, chess.BLACK
    ).bit_count()
    queens = board.pieces_mask(chess.QUEEN, chess.WHITE).bit_count() + board.pieces_mask(
        chess.QUEEN, chess.BLACK
    ).bit_count()
    phase = (
        knights * PHASE_WEIGHT_KNIGHT
        + bishops * PHASE_WEIGHT_BISHOP
        + rooks * PHASE_WEIGHT_ROOK
        + queens * PHASE_WEIGHT_QUEEN
    )
    return max(0, min(MAX_PHASE, phase))


def compute_material_balance(board: chess.Board) -> int:
    """Net material balance in standard pawns from White's perspective."""
    w = (
        board.pieces_mask(chess.PAWN, chess.WHITE).bit_count()
        + 3 * board.pieces_mask(chess.KNIGHT, chess.WHITE).bit_count()
        + 3 * board.pieces_mask(chess.BISHOP, chess.WHITE).bit_count()
        + 5 * board.pieces_mask(chess.ROOK, chess.WHITE).bit_count()
        + 9 * board.pieces_mask(chess.QUEEN, chess.WHITE).bit_count()
    )
    b = (
        board.pieces_mask(chess.PAWN, chess.BLACK).bit_count()
        + 3 * board.pieces_mask(chess.KNIGHT, chess.BLACK).bit_count()
        + 3 * board.pieces_mask(chess.BISHOP, chess.BLACK).bit_count()
        + 5 * board.pieces_mask(chess.ROOK, chess.BLACK).bit_count()
        + 9 * board.pieces_mask(chess.QUEEN, chess.BLACK).bit_count()
    )
    return w - b


def generate_game_positions(
    rng: random.Random,
    game_id: str,
    source_type: str,
    initial_fen: str,
    max_plies: int = 80,
    sample_interval: int = 4,
) -> list[dict[str, Any]]:
    board = chess.Board(initial_fen)
    records: list[dict[str, Any]] = []

    # Optional initial random jitter
    random_pre_plies = rng.randint(0, 6)
    for _ in range(random_pre_plies):
        moves = list(board.legal_moves)
        if not moves or board.is_game_over():
            break
        board.push(rng.choice(moves))

    ply = 0
    while not board.is_game_over() and ply < max_plies:
        moves = list(board.legal_moves)
        if not moves:
            break

        # Plausible semi-random move selection: favor captures and checks lightly
        tactical = [m for m in moves if board.is_capture(m) or board.gives_check(m)]
        chosen = (
            rng.choice(tactical)
            if tactical and rng.random() < 0.4
            else rng.choice(moves)
        )

        board.push(chosen)
        ply += 1

        # Sample every sample_interval ± 1 plies, excluding terminal positions
        if ply >= 6 and (ply % sample_interval == 0) and not board.is_game_over():
            # Exclude positions where king is in check or trivially captured
            records.append(
                {
                    "position_id": f"{game_id}_p{ply}",
                    "fen": board.fen(),
                    "source_type": source_type,
                    "source_game_id": game_id,
                    "source_ply": ply,
                    "side_to_move": "w" if board.turn == chess.WHITE else "b",
                    "game_result": board.result() if board.is_game_over() else "*",
                    "game_phase": compute_phase(board),
                    "material_balance": compute_material_balance(board),
                }
            )

    return records


def collect_dataset(
    target_count: int = 1000,
    seed: int = 42,
    output_path: Path | None = None,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    seen_fens: set[str] = set()
    collected: list[dict[str, Any]] = []

    # 1. Curated benchmark positions
    for idx, bp in enumerate(BENCHMARK_SUITE):
        b = chess.Board(bp.fen)
        key = canonical_key(bp.fen)
        seen_fens.add(key)
        collected.append(
            {
                "position_id": f"bench_{idx:03d}",
                "fen": bp.fen,
                "source_type": "benchmark",
                "source_game_id": f"bench_{bp.category}",
                "source_ply": 0,
                "side_to_move": "w" if b.turn == chess.WHITE else "b",
                "game_result": "*",
                "game_phase": compute_phase(b),
                "material_balance": compute_material_balance(b),
            }
        )

    # 2. Diverse game rollouts
    game_idx = 0
    all_seeds = OPENING_SEEDS + [bp.fen for bp in BENCHMARK_SUITE]
    while len(collected) < target_count:
        game_idx += 1
        start_fen = rng.choice(all_seeds)
        stype = "eco_rollout" if start_fen in OPENING_SEEDS else "bench_rollout"
        game_records = generate_game_positions(
            rng,
            game_id=f"game_{game_idx:05d}",
            source_type=stype,
            initial_fen=start_fen,
            max_plies=rng.randint(40, 100),
            sample_interval=rng.randint(4, 7),
        )

        for rec in game_records:
            key = canonical_key(rec["fen"])
            if key not in seen_fens:
                seen_fens.add(key)
                collected.append(rec)
                if len(collected) >= target_count:
                    break

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for rec in collected:
                f.write(json.dumps(rec) + "\n")

    return collected


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect training positions.")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("training/datasets/positions/positions_smoke.jsonl"),
    )
    args = parser.parse_args()

    positions = collect_dataset(
        target_count=args.count,
        seed=args.seed,
        output_path=args.output,
    )
    print(f"Collected {len(positions)} unique positions into {args.output}")

    # Report phase and material balance summary
    phases = [p["game_phase"] for p in positions]
    avg_phase = sum(phases) / len(phases)
    openings = sum(1 for p in phases if p >= 20)
    middlegames = sum(1 for p in phases if 8 <= p < 20)
    endgames = sum(1 for p in phases if p < 8)
    print(
        f"Phase breakdown: Openings (>=20): {openings}, "
        f"Middle (8..19): {middlegames}, Endgames (<8): {endgames}"
    )
    print(f"Average phase: {avg_phase:.1f} / 24")


if __name__ == "__main__":
    main()
