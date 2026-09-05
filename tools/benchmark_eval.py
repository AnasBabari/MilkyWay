"""Eval benchmark: positions/sec for the handcrafted evaluation."""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess  # noqa: E402

from evaluation import evaluate  # noqa: E402


def random_position(rng: random.Random, plies: int) -> chess.Board:
    board = chess.Board()
    for _ in range(plies):
        moves = list(board.legal_moves)
        if not moves or board.is_game_over():
            break
        board.push(rng.choice(moves))
    return board


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark MilkyWay evaluation throughput.")
    parser.add_argument("--positions", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    positions = [random_position(rng, rng.randint(10, 60)).fen() for _ in range(args.positions)]
    boards = [chess.Board(fen) for fen in positions]
    started = time.perf_counter()
    total = 0
    for board in boards:
        total += evaluate(board)
    elapsed = time.perf_counter() - started
    print(
        f"evaluated {len(boards)} positions in {elapsed:.2f}s = {len(boards) / elapsed:.0f} eval/s"
    )
    print(f"checksum {total}")


if __name__ == "__main__":
    main()
