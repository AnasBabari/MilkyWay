"""Benchmark Candidate vs MW-0.2 on endgame positions under the 600-ply harness."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.referee import play_match  # noqa: E402
from harness.sandbox import local  # noqa: E402
from tools.benchmark_positions import BENCHMARK_SUITE  # noqa: E402


def main() -> None:
    candidate = ROOT
    mw02 = ROOT / "versions" / "mw_0_2"
    endgames = [p for p in BENCHMARK_SUITE if "ending" in p.category]
    print(f"Testing {len(endgames)} endgame positions (paired, {len(endgames)*2} games total)...")

    results = {"wins": 0, "draws": 0, "losses": 0}
    terms: dict[str, int] = {}

    for pos in endgames:
        for cand_white in (True, False):
            w, b = (candidate, mw02) if cand_white else (mw02, candidate)
            out = play_match(local(w), local(b), 5000, 100, ply_cap=600, start_fen=pos.fen)
            terms[out.termination] = terms.get(out.termination, 0) + 1
            side = "W" if cand_white else "B"
            if out.result in ("draw", "void"):
                results["draws"] += 1
                tag = "="
            elif (out.result == "white") == cand_white:
                results["wins"] += 1
                tag = "+"
            else:
                results["losses"] += 1
                tag = "-"
            print(f"[{pos.id}] cand={side}: {tag} {out.result} by {out.termination}")

    total = sum(results.values())
    score = (results["wins"] + results["draws"] / 2.0) / total if total else 0.0
    print("\nEndgame Arena Result:")
    print(f"Score: {score:.1%} (+{results['wins']} ={results['draws']} -{results['losses']})")
    print(f"Terminations: {terms}")


if __name__ == "__main__":
    main()
