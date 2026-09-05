"""Search benchmark: fixed-budget move times over a set of positions."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess  # noqa: E402

import agent  # noqa: E402

POSITIONS: tuple[str, ...] = (
    chess.STARTING_FEN,
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 0 1",
    "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 4 3",
    "rnbqkb1r/pp2pppp/5n2/3p4/3P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 0 1",
    "2rr3k/pp3pp1/1nn2n1p/3p4/3P4/2N1PN1P/PP3PP1/2RR3K w - - 0 1",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Time get_move over sample positions.")
    parser.add_argument("--time-ms", type=int, default=2000)
    parser.add_argument("--repeat", type=int, default=2)
    args = parser.parse_args()

    for fen in POSITIONS:
        times: list[float] = []
        move_uci = "0000"
        for _ in range(args.repeat):
            started = time.monotonic()
            move_uci = agent.get_move(fen, args.time_ms)
            times.append((time.monotonic() - started) * 1000.0)
        board = chess.Board(fen)
        legal = chess.Move.from_uci(move_uci) in board.legal_moves
        avg = sum(times) / len(times)
        print(f"{fen[:40]:42s} -> {move_uci:6s} legal={legal} avg={avg:.0f}ms")


if __name__ == "__main__":
    main()
