"""Detailed profiler and benchmark harness for MilkyWay search and evaluation.

Instruments:
- cProfile call breakdowns (eval, ordering, TT, push/pop, check detection)
- Node and qnode distributions
- NPS and depth reached
- Profiling of quiet-check ordering overhead
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

# Add repo root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess  # noqa: E402

from engine import MilkyWayEngine  # noqa: E402
from time_manager import Clock  # noqa: E402
from tools.benchmark_positions import BENCHMARK_SUITE  # noqa: E402


def profile_suite(
    positions_count: int = 10,
    depth: int = 4,
    time_ms: int | None = None,
) -> None:
    positions = BENCHMARK_SUITE[:positions_count]
    print(f"=== Profiling MilkyWay across {len(positions)} positions ===")
    print(f"Mode: {'fixed depth ' + str(depth) if time_ms is None else f'fixed time {time_ms}ms'}")

    profiler = cProfile.Profile()
    total_nodes = 0
    total_qnodes = 0
    total_elapsed = 0.0
    engine = MilkyWayEngine()

    profiler.enable()
    start_all = time.perf_counter()

    for pos in positions:
        engine.reset_game()
        board = chess.Board(pos.fen)
        if time_ms is not None:
            # Fixed time via engine choose_move
            t0 = time.perf_counter()
            best_uci = engine.choose_move(pos.fen, time_ms)
            best_move = chess.Move.from_uci(best_uci)
            elapsed = time.perf_counter() - t0
        else:
            # Fixed depth
            t0 = time.perf_counter()
            legal = list(board.legal_moves)
            legal_sorted = sorted(legal, key=lambda m: m.uci())
            fallback = engine._quick_fallback(board, legal_sorted)
            clock = Clock()
            # Far in future deadline
            clock.soft_deadline = time.monotonic() + 1000.0
            clock.hard_deadline = time.monotonic() + 1000.0
            engine.searcher.new_search(clock, emergency=False)
            best_move, _score, _pv = engine.searcher.iterative_deepening(
                board, depth, fallback
            )
            elapsed = time.perf_counter() - t0

        stats = engine.searcher.stats
        total_nodes += stats.nodes
        total_qnodes += stats.qnodes
        total_elapsed += elapsed
        nps = int((stats.nodes + stats.qnodes) / max(1e-5, elapsed))
        print(
            f"[{pos.id:12s}] {pos.category:22s} -> {best_move.uci():6s} "
            f"depth={stats.depth_reached} nodes={stats.nodes:6d} qnodes={stats.qnodes:6d} "
            f"time={elapsed*1000:6.1f}ms nps={nps:6d}"
        )

    wall_time = time.perf_counter() - start_all
    profiler.disable()

    all_nodes = total_nodes + total_qnodes
    overall_nps = int(all_nodes / max(1e-5, total_elapsed))
    print("\n=== Aggregate Search Metrics ===")
    print(f"Total positions: {len(positions)}")
    print(f"Total wall time: {wall_time:.3f}s (search time: {total_elapsed:.3f}s)")
    print(f"Total nodes: {total_nodes:,} | Qnodes: {total_qnodes:,} | All nodes: {all_nodes:,}")
    print(f"Overall NPS: {overall_nps:,}")

    # Process cProfile stats
    stream = io.StringIO()
    ps = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    ps.print_stats(35)
    print("\n=== cProfile Cumulative Time (Top 35) ===")
    print(stream.getvalue())

    # Time breakdown by key functions
    stream_time = io.StringIO()
    ps_time = pstats.Stats(profiler, stream=stream_time).sort_stats("time")
    ps_time.print_stats(30)
    print("\n=== cProfile Self Time (Top 30) ===")
    print(stream_time.getvalue())


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile MilkyWay search.")
    parser.add_argument(
        "--positions", type=int, default=10, help="Number of benchmark positions to run"
    )
    parser.add_argument("--depth", type=int, default=4, help="Fixed depth for search")
    parser.add_argument("--time-ms", type=int, default=None, help="Fixed time ms per position")
    args = parser.parse_args()

    profile_suite(positions_count=args.positions, depth=args.depth, time_ms=args.time_ms)


if __name__ == "__main__":
    main()
