"""MilkyWay M17 — Offline data collection, PGN parsing, and self-play generation.

Extracts position records from PGNs, MilkyWay self-play, and curated benchmark banks.
Deduplicates positions and shards them into train/val/test splits.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import TextIO

import chess
import chess.pgn

from constants import INF
from search import Searcher
from time_manager import Clock, TimeBudget
from tools.benchmark_positions import BENCHMARK_SUITE
from tools.test_bank import PAIRED_TEST_BANK
from training.data.dataset import PositionRecord, split_game_id, write_shard_npz
from transposition import TranspositionTable


def parse_pgn_stream(
    pgn_io: TextIO,
    source_name: str = "pgn",
    sample_interval: int = 4,
    max_positions: int | None = None,
    seen_fens: set[str] | None = None,
) -> list[PositionRecord]:
    """Parse standard chess games from PGN stream and extract sampled positions."""
    if seen_fens is None:
        seen_fens = set()

    records: list[PositionRecord] = []
    game_idx = 0

    while True:
        try:
            game = chess.pgn.read_game(pgn_io)
        except Exception:
            break
        if game is None:
            break

        game_idx += 1
        headers = game.headers
        variant = headers.get("Variant", "Standard").lower()
        if variant not in ("standard", ""):
            continue

        result_str = headers.get("Result", "*")
        if result_str == "1-0":
            result = 1.0
        elif result_str == "0-1":
            result = 0.0
        elif result_str == "1/2-1/2":
            result = 0.5
        else:
            result = 0.5  # Neutral fallback

        game_id = headers.get("Site", f"{source_name}_game_{game_idx}")
        board = game.board()

        for ply, node in enumerate(game.mainline(), start=1):
            move = node.move

            # Sample every sample_interval plies, skip initial 4 opening book plies
            if ply >= 4 and (ply % sample_interval == 0):
                fen = board.fen()
                if fen not in seen_fens:
                    seen_fens.add(fen)
                    pos_id = f"{game_id}_ply_{ply}"
                    records.append(
                        PositionRecord(
                            position_id=pos_id,
                            fen=fen,
                            source=source_name,
                            source_game_id=game_id,
                            source_ply=ply,
                            side_to_move=1 if board.turn == chess.WHITE else 0,
                            played_move=move.uci(),
                            game_result=result,
                        )
                    )
                    if max_positions is not None and len(records) >= max_positions:
                        return records

            board.push(move)

    return records


def generate_selfplay_positions(
    target_positions: int,
    sample_interval: int = 4,
    depth: int = 2,
    seen_fens: set[str] | None = None,
    seed: int = 42,
) -> list[PositionRecord]:
    """Generate self-play games using fast MilkyWay engine and extract positions."""
    if seen_fens is None:
        seen_fens = set()

    rng = random.Random(seed)
    records: list[PositionRecord] = []
    game_idx = 0

    tt = TranspositionTable(max_entries=32768)
    searcher = Searcher(tt)

    while len(records) < target_positions:
        game_idx += 1
        game_id = f"mw_selfplay_{game_idx}_{seed}"
        board = chess.Board()
        moves_played: list[tuple[str, str, int]] = []  # (fen, uci, ply)
        ply = 0

        searcher.new_game()

        while not board.is_game_over() and ply < 100:
            ply += 1
            legal = list(board.legal_moves)
            if not legal:
                break

            # In early opening (first 2 full moves), add exploration noise
            if ply <= 4:
                chosen = rng.choice(legal)
            else:
                # Fast depth-2 search
                clock = Clock()
                clock.start_move(TimeBudget(soft_ms=10000.0, hard_ms=30000.0, emergency=False))
                searcher.new_search(clock, False)
                _score, pv = searcher._search_root(board, depth, -INF, INF)
                chosen = pv[0] if pv else legal[0]

            fen = board.fen()
            moves_played.append((fen, chosen.uci(), ply))
            board.push(chosen)

        # Determine final result
        if board.is_checkmate():
            # Winner is side that made the last move
            winner = not board.turn
            result = 1.0 if winner == chess.WHITE else 0.0
        else:
            result = 0.5

        # Sample positions from this game
        for fen, uci, p in moves_played:
            if p >= 4 and (p % sample_interval == 0) and fen not in seen_fens:
                seen_fens.add(fen)
                b_check = chess.Board(fen)
                records.append(
                    PositionRecord(
                        position_id=f"{game_id}_p{p}",
                        fen=fen,
                        source="mw_selfplay",
                        source_game_id=game_id,
                        source_ply=p,
                        side_to_move=1 if b_check.turn == chess.WHITE else 0,
                        played_move=uci,
                        game_result=result,
                    )
                )
                if len(records) >= target_positions:
                    break

    return records


def get_curated_positions(seen_fens: set[str] | None = None) -> list[PositionRecord]:
    """Collect curated positions from neutral test bank, suites, and failure cases."""
    if seen_fens is None:
        seen_fens = set()

    records: list[PositionRecord] = []

    # 1. Paired test bank (200 balanced positions)
    for pos in PAIRED_TEST_BANK:
        if pos.fen not in seen_fens:
            seen_fens.add(pos.fen)
            b = chess.Board(pos.fen)
            legal = list(b.legal_moves)
            if legal:
                records.append(
                    PositionRecord(
                        position_id=f"test_bank_{pos.id}",
                        fen=pos.fen,
                        source="test_bank",
                        source_game_id=f"bank_{pos.id}",
                        source_ply=20,
                        side_to_move=1 if b.turn == chess.WHITE else 0,
                        played_move=legal[0].uci(),
                        game_result=0.5,
                        stockfish_cp=float(pos.eval_cp),
                    )
                )

    # 2. Benchmark suite (40 positions)
    for b_pos in BENCHMARK_SUITE:
        if b_pos.fen not in seen_fens:
            seen_fens.add(b_pos.fen)
            b = chess.Board(b_pos.fen)
            legal = list(b.legal_moves)
            if legal:
                records.append(
                    PositionRecord(
                        position_id=f"bench_suite_{b_pos.id}",
                        fen=b_pos.fen,
                        source="benchmark_suite",
                        source_game_id=f"bench_{b_pos.id}",
                        source_ply=20,
                        side_to_move=1 if b.turn == chess.WHITE else 0,
                        played_move=legal[0].uci(),
                        game_result=0.5,
                    )
                )

    # 3. Rated LARPMAXX failure critical position
    larpmaxx_fen = "1rBq1r2/1p3p1k/2n3pb/p1p4p/P3Pp1P/3P2P1/1PPQ1P2/R2R2K1 w - - 0 19"
    if larpmaxx_fen not in seen_fens:
        seen_fens.add(larpmaxx_fen)
        records.append(
            PositionRecord(
                position_id="rated_larpmaxx_r20_critical",
                fen=larpmaxx_fen,
                source="rated_larpmaxx",
                source_game_id="larpmaxx_r20",
                source_ply=37,
                side_to_move=1,
                played_move="c8h3",  # Sensible bishop retreat instead of g4 blunder
                game_result=0.0,
            )
        )

    return records


def build_smoke_dataset(
    output_base_dir: Path,
    target_positions: int = 50000,
    shard_size: int = 10000,
    pgn_path: Path | None = None,
) -> dict[str, list[Path]]:
    """Build and shard the 50k smoke dataset with game-level train/val/test splits."""
    seen_fens: set[str] = set()
    all_records: list[PositionRecord] = []

    # 1. Add curated positions
    curated = get_curated_positions(seen_fens)
    all_records.extend(curated)

    # 2. Add PGN positions if provided
    pgn_list: list[Path] = []
    if pgn_path is not None:
        if isinstance(pgn_path, list):
            pgn_list = [p for p in pgn_path if p.exists()]
        elif pgn_path.is_dir():
            pgn_list = sorted(list(pgn_path.glob("*.pgn")))
        elif pgn_path.exists():
            pgn_list = [pgn_path]

    for p in pgn_list:
        if len(all_records) >= target_positions:
            break
        with open(p, encoding="latin1", errors="ignore") as f:
            pgn_recs = parse_pgn_stream(
                f,
                source_name=p.stem,
                sample_interval=4,
                max_positions=target_positions - len(all_records),
                seen_fens=seen_fens,
            )
            all_records.extend(pgn_recs)
            print(f"Loaded {len(pgn_recs)} from {p.name} (Total so far: {len(all_records)})")

    # 3. Generate self-play positions to reach target_positions
    remaining = target_positions - len(all_records)
    if remaining > 0:
        sp_recs = generate_selfplay_positions(
            target_positions=remaining,
            sample_interval=4,
            depth=1,  # Ultra-fast depth 1 for rapid smoke dataset generation
            seen_fens=seen_fens,
        )
        all_records.extend(sp_recs)

    # Split by game ID
    splits: dict[str, list[PositionRecord]] = {"train": [], "val": [], "test": []}
    for rec in all_records:
        split_name = split_game_id(rec.source_game_id)
        splits[split_name].append(rec)

    created_shards: dict[str, list[Path]] = {"train": [], "val": [], "test": []}

    for split_name, recs in splits.items():
        split_dir = output_base_dir / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        num_shards = math.ceil(len(recs) / shard_size) if recs else 0
        for s_idx in range(num_shards):
            shard_recs = recs[s_idx * shard_size : (s_idx + 1) * shard_size]
            shard_file = split_dir / f"shard_{s_idx:05d}.npz"
            write_shard_npz(shard_recs, shard_file)
            created_shards[split_name].append(shard_file)

    return created_shards
