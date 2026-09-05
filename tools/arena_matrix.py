"""Arena matrix helper: record MilkyWay vs named opponents (appends BENCHMARKS.md)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_arena(opponent: str, games: int, base_ms: int, increment_ms: int) -> str:
    cmd = [
        sys.executable,
        "-m",
        "harness.arena",
        "--opponent",
        opponent,
        "--games",
        str(games),
        "--base-ms",
        str(base_ms),
        "--increment-ms",
        str(increment_ms),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd(), check=False)
    output = (proc.stdout or "") + (proc.stderr or "")
    print(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small opponent matrix.")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--base-ms", type=int, default=10000)
    parser.add_argument("--increment-ms", type=int, default=100)
    parser.add_argument(
        "--opponents",
        nargs="+",
        default=["baselines/random", "baselines/greedy", "baselines/minimax", "baselines/numba"],
    )
    args = parser.parse_args()
    for opponent in args.opponents:
        print(f"=== MilkyWay vs {opponent} ===")
        run_arena(opponent, args.games, args.base_ms, args.increment_ms)


if __name__ == "__main__":
    main()
