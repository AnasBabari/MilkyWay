"""Timing probe: get_move must respect its budget, especially tiny ones.

A flag loss means elapsed wall time exceeded the remaining clock. This hammers
the emergency path (30 ms to 1 s budgets) over random positions with fresh
engine state. Any overrun is printed; the run fails if one occurs.

Slow (~minutes); run before tagging a release, not on every commit.
"""

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

from engine import MilkyWayEngine  # noqa: E402


def random_fen(rng: random.Random, max_plies: int) -> str:
    board = chess.Board()
    for _ in range(rng.randint(5, max_plies)):
        moves = list(board.legal_moves)
        if not moves or board.is_game_over():
            break
        board.push(rng.choice(moves))
    for _ in range(8):
        if not board.is_game_over() and list(board.legal_moves):
            return board.fen()
        if not board.move_stack:
            return chess.STARTING_FEN
        board.pop()
    return chess.STARTING_FEN


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe low-clock deadline safety.")
    parser.add_argument("--calls", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260905)
    parser.add_argument(
        "--budgets", type=int, nargs="+", default=[30, 50, 75, 100, 150, 250, 500, 1000]
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    violations = 0
    total = 0
    for budget in args.budgets:
        worst = -1e9
        for _ in range(args.calls):
            eng = MilkyWayEngine()
            fen = random_fen(rng, 70)
            started = time.perf_counter()
            uci = eng.choose_move(fen, budget)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            board = chess.Board(fen)
            assert chess.Move.from_uci(uci) in board.legal_moves, (uci, fen)
            over = elapsed_ms - budget
            worst = max(worst, over)
            total += 1
            if over > 0:
                violations += 1
                print(f"budget={budget}ms elapsed={elapsed_ms:.1f}ms OVER by {over:.1f}ms")
        print(f"budget={budget}ms: worst overrun {worst:+.1f}ms ({args.calls} calls)")
    print(f"\n{violations}/{total} calls exceeded budget")
    if violations:
        raise SystemExit(f"{violations} budget overruns")


if __name__ == "__main__":
    main()
