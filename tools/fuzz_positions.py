"""Fuzzing: random legal playouts must never crash or return illegal moves."""

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

import agent  # noqa: E402


def random_plies_position(rng: random.Random, max_plies: int) -> str:
    board = chess.Board()
    for _ in range(rng.randint(0, max_plies)):
        moves = list(board.legal_moves)
        if not moves or board.is_game_over():
            break
        board.push(rng.choice(moves))
        if board.is_game_over():
            break
    # Only return non-terminal positions with legal moves.
    for _ in range(10):
        if not board.is_game_over() and list(board.legal_moves):
            return board.fen()
        board.pop() if board.move_stack else None
        if not board.move_stack:
            return chess.STARTING_FEN
    return chess.STARTING_FEN


def main() -> None:
    parser = argparse.ArgumentParser(description="Fuzz get_move over random positions.")
    parser.add_argument("--positions", type=int, default=500)
    parser.add_argument("--time-ms", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    failures = 0
    slowest = 0.0
    started_all = time.monotonic()
    for i in range(args.positions):
        fen = random_plies_position(rng, 80)
        board = chess.Board(fen)
        before = board.fen()
        started = time.monotonic()
        try:
            move_uci = agent.get_move(fen, args.time_ms)
        except Exception as exc:
            failures += 1
            print(f"[{i}] EXCEPTION {exc!r} fen={fen}")
            continue
        elapsed_ms = (time.monotonic() - started) * 1000.0
        slowest = max(slowest, elapsed_ms)
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            failures += 1
            print(f"[{i}] MALFORMED {move_uci!r} fen={fen}")
            continue
        if move not in board.legal_moves:
            failures += 1
            print(f"[{i}] ILLEGAL {move_uci!r} fen={fen}")
            continue
        if chess.Board(fen).fen() != before:
            failures += 1
            print(f"[{i}] BOARD MUTATED fen={fen}")
        if elapsed_ms > args.time_ms + 1500:
            print(f"[{i}] SLOW {elapsed_ms:.0f}ms (budget {args.time_ms}ms) fen={fen}")
        if (i + 1) % 100 == 0:
            print(f"... {i + 1}/{args.positions} failures={failures}")
    total_s = time.monotonic() - started_all
    print(f"done: {args.positions} positions, {failures} failures")
    print(f"slowest {slowest:.0f}ms over {total_s:.1f}s")
    if failures:
        raise SystemExit(f"{failures} fuzz failures")


if __name__ == "__main__":
    main()
