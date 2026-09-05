"""Paired arena: play each benchmark FEN twice, colours reversed.

Closer to the rated format (curated neutral positions) than repeated
standard-start games, and cleaner for A/B testing: every position is
played once per colour, so opening luck cancels out.

Usage:
    python tools/paired_arena.py --opponent versions/mw_0_1 --games-per-side 1
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.arena import FAST_BASE_MS, FAST_INCREMENT_MS  # noqa: E402
from harness.referee import FAILED_TERMINATIONS, play_match  # noqa: E402
from harness.rules import PLY_CAP  # noqa: E402
from harness.sandbox import local  # noqa: E402
from tools.benchmark_positions import BENCHMARK_SUITE  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Paired FEN-bank arena.")
    parser.add_argument("--agent", type=Path, default=Path("."))
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--positions", type=int, default=len(BENCHMARK_SUITE))
    parser.add_argument("--base-ms", type=int, default=FAST_BASE_MS)
    parser.add_argument("--increment-ms", type=int, default=FAST_INCREMENT_MS)
    parser.add_argument("--ply-cap", type=int, default=PLY_CAP)
    args = parser.parse_args()

    agent = args.agent.resolve()
    opponent = args.opponent.resolve()
    positions = BENCHMARK_SUITE[: args.positions]
    wins = draws = losses = 0
    terminations: dict[str, int] = {}
    total = 0
    started = time.perf_counter()
    for pos in positions:
        for agent_white in (True, False):
            total += 1
            white, black = (agent, opponent) if agent_white else (opponent, agent)
            outcome = play_match(
                local(white), local(black), args.base_ms, args.increment_ms,
                ply_cap=args.ply_cap, start_fen=pos.fen,
            )
            terminations[outcome.termination] = terminations.get(outcome.termination, 0) + 1
            if outcome.result in ("draw", "void"):
                draws += 1
                tag = "="
            elif (outcome.result == "white") == agent_white:
                wins += 1
                tag = "+"
            else:
                losses += 1
                tag = "-"
            print(f"[{total}] {pos.id} agent={'W' if agent_white else 'B'} "
                  f"{tag} {outcome.result} by {outcome.termination}", flush=True)
    score = (wins + draws / 2) / total if total else 0.0
    print(f"\n{agent} vs {opponent} over {total} paired games ({len(positions)} positions x2)")
    print(f"+{wins} ={draws} -{losses}, score {score:.1%}")
    print("terminations: " + ", ".join(f"{n} {c}" for n, c in terminations.items()))
    print(f"elapsed {time.perf_counter() - started:.0f}s")
    broken = {n: c for n, c in terminations.items() if n in FAILED_TERMINATIONS}
    if broken:
        detail = ", ".join(f"{n} {c}" for n, c in broken.items())
        raise SystemExit(f"agent failed to finish: {detail}")


if __name__ == "__main__":
    main()
