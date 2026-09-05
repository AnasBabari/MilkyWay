# MilkyWay — Benchmarks

All results are `agent (./MilkyWay) vs opponent`, alternating colours (even game = agent White).
Time controls noted per row. Harness: `harness/arena.py` / `harness/play.py` (unmodified).

## M0 — Unmodified starter baseline (random mover, 2026-09-05, local Windows, uv sync)

Environment: Python 3.14.5 (local; platform is 3.12), chess 1.11.2, numpy 2.5.2,
numba 0.67.0, torch 2.13.0+cpu, onnxruntime 1.29.0. Local machine (not EPYC 9V74).

| Date | Matchup | Games | TC | Score | W/D/L | Terminations | Notes |
|------|---------|-------|----|-------|-------|--------------|-------|
| 2026-09-05 | starter(random) vs baselines/random | 2 | 5s+0.1s(?) `--base-ms 5000` | 50.0% | +1 =0 -1 | adjudication 2 | `make gate` smoke: ruff OK, mypy OK |
| 2026-09-05 | starter(random) vs baselines/greedy | 20 | 10s+0.1s (arena default) | 10.0% | +0 =4 -16 | stalemate 4, checkmate 16 | matches README (~10%) |
| 2026-09-05 | starter(random) vs baselines/minimax | 6 | 10s+0.1s | 8.3% | +0 =1 -5 | checkmate 5, threefold 1 | expected: random loses |
| 2026-09-05 | starter(random, White) vs greedy(Black), single `harness.play` | 1 | 120s+0.5s | draw | =1 | threefold_repetition | sanity: full-TC game finishes cleanly |

README reference (upstream, tiny samples): random vs greedy 10.0% (20 games, 10s+0.1s);
greedy vs minimax 0.0% (6 games, 120s+0.5s); numba vs minimax 66.7% (+2 =4 -0, 6 games).

No crashes / illegal moves / flags in M0 baseline runs.

## Milestone results (append below)

<!-- New entries: MW-x.y vs opponent, games, TC, W/D/L, score, change description -->
