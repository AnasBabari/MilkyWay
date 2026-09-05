"""Benchmark harness to compare Move Ordering and Evaluation variants."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess  # noqa: E402

from engine import MilkyWayEngine  # noqa: E402
from time_manager import Clock  # noqa: E402
from tools.benchmark_positions import BENCHMARK_SUITE  # noqa: E402


def run_benchmark(
    positions_count: int = 20,
    depth: int = 4,
    time_ms: int | None = None,
) -> dict[str, float | int]:
    positions = BENCHMARK_SUITE[:positions_count]
    total_nodes = 0
    total_qnodes = 0
    total_elapsed = 0.0
    engine = MilkyWayEngine()

    for pos in positions:
        engine.reset_game()
        board = chess.Board(pos.fen)
        if time_ms is not None:
            t0 = time.perf_counter()
            _ = engine.choose_move(pos.fen, time_ms)
            elapsed = time.perf_counter() - t0
        else:
            t0 = time.perf_counter()
            legal = list(board.legal_moves)
            legal_sorted = sorted(legal, key=lambda m: m.uci())
            fallback = engine._quick_fallback(board, legal_sorted)
            clock = Clock()
            clock.soft_deadline = time.monotonic() + 1000.0
            clock.hard_deadline = time.monotonic() + 1000.0
            engine.searcher.new_search(clock, emergency=False)
            _best_move, _score, _pv = engine.searcher.iterative_deepening(
                board, depth, fallback
            )
            elapsed = time.perf_counter() - t0

        stats = engine.searcher.stats
        total_nodes += stats.nodes
        total_qnodes += stats.qnodes
        total_elapsed += elapsed

    all_nodes = total_nodes + total_qnodes
    nps = int(all_nodes / max(1e-5, total_elapsed))
    return {
        "nodes": total_nodes,
        "qnodes": total_qnodes,
        "all_nodes": all_nodes,
        "elapsed": total_elapsed,
        "nps": nps,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--positions", type=int, default=20)
    parser.add_argument("--depth", type=int, default=4)
    args = parser.parse_args()
    res = run_benchmark(positions_count=args.positions, depth=args.depth)
    print(f"Results: {res}")


if __name__ == "__main__":
    main()
