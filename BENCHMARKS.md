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

### MW-0.1 — first competition engine (2026-09-05, local Windows, uv sync)

Classical engine, no network. Tapered eval (material, PST, pawn structure,
bishop pair, rooks, mobility, king safety, mop-up) + ID + PVS alpha-beta +
TT + MVV-LVA/killer/history ordering + quiescence + aspiration + LMR +
null-move + futility/reverse-futility + check extensions. Eval ~5.2k/s
(`tools/benchmark_eval.py`, 2000 positions). Fuzz 200/200 clean @200ms.
Unit tests 32/32. ruff + mypy strict clean (30 files). Zip 57 KB unzipped.

| Date | Matchup | Games | TC | Score | W/D/L | Terminations | Notes |
|------|---------|-------|----|-------|-------|--------------|-------|
| 2026-09-05 | MW-0.1 vs baselines/random | 2 | 5s+0.1s | 100% | +2 =0 -0 | checkmate 2 | gate smoke |
| 2026-09-05 | MW-0.1 vs baselines/greedy | 6 | 10s+0.1s | 100% | +6 =0 -0 | checkmate 6 | |
| 2026-09-05 | MW-0.1 vs baselines/greedy | 20 | 10s+0.1s | 100% | +20 =0 -0 | checkmate 20 | wins both colours |
| 2026-09-05 | MW-0.1 vs baselines/minimax | 6 | 10s+0.1s | 100% | +6 =0 -0 | checkmate 6 | |
| 2026-09-05 | MW-0.1 vs baselines/numba | 6 | 10s+0.1s | 91.7% | +5 =1 -0 | checkmate 5, threefold 1 | |
| 2026-09-05 | MW-0.1 vs baselines/numba | 20 | 10s+0.1s | 97.5% | +19 =1 -0 | checkmate 19, threefold 1 | strongest baseline beaten |

Zero illegal moves / crashes / flags across all MW-0.1 games (58 games total).

### MW-0.2 — performance release (2026-09-05, local Windows, uv sync)

Rule for the release: PROFILE → HYPOTHESIS → ONE CHANGE → MEASURE →
ARENA → KEEP OR REVERT. No new search features; no neural network.

**Profile (cProfile, fixed depth 4, 6 suite positions, current tree).**
Total 13.5 s: move generation 31% (`generate_legal_moves`, python-chess),
evaluation 37% cumulative (king-safety `is_attacked_by` alone ~18%,
pawn structure, mobility), `is_capture` 1.3M calls, ordering 4%.
Eval is a real slice; movegen is the ceiling (poor JIT candidate).

**Changes kept (each measured, game-tested as a bundle).**
- Bitboard evaluation rewrite: single pass over `pieces_mask` ints, inline
  mobility via `attacks_mask().bit_count()`, mask-based passer detection,
  no `piece_map()` dicts, no `SquareSet` temporaries. Standalone eval
  5225 → 14774/s (**2.83x**). Differential-tested bit-identical to MW-0.1
  on 2000 + 2000 random positions (`tools/diff_eval.py`, 0 mismatches).
- Quiet-check ordering bonus removed: the per-quiet-move
  push → `is_check()` → pop probe is gone; ordering is TT move,
  promotions, MVV-LVA, killers, history. Fixed-depth node counts within
  2.4% of MW-0.1, so ordering quality is preserved.
- MVV-LVA via `piece_type_at` (no `Piece` objects); integer move tie-break
  instead of UCI strings in ordering sort.
- TT eviction O(1) FIFO. Justification: measured TT growth ~550 stores per
  move at 8 s/move (~5.5k entries after 10 moves); a 131k-entry table can
  fill in long games, where the old per-store full-table scan would cost
  seconds per move exactly when games matter most. FIFO keeps fresh
  entries, which dominate hit rate.

**Fixed-depth comparison (20 suite positions, depth 4).**
MW-0.1: 170,911 nodes / 33.95 s = 5034 NPS.
MW-0.2: 174,995 nodes / 16.64 s = 10519 NPS (**2.09x**, same work).

**Arena: MW-0.2 vs MW-0.1, 100 games, 10 s + 0.1 s, alternating colours.**
+93 =6 -1, **score 96.0%**. Terminations: checkmate 93,
threefold 4, fifty-moves 2, flag 1 (see reliability note).

**Reliability incident: 1 flag by MW-0.2 (game 46, as Black).**
Root cause found by timing probe (320 calls, 30–1000 ms budgets):
67 overruns, all at ≤75 ms budgets (worst +36 ms at 50 ms). Two defects:
(1) absolute `MIN_HARD_MS = 60` floor let the hard deadline exceed the
remaining clock; (2) 256-node poll granularity (~25 ms) is larger than a
tiny hard budget. Fix: proportional safety margin
(`hard ≤ clock − min(300, clock/2)`, 20 ms protocol floor, never above the
clock), 64-node polling in emergency, instant fallback reply below 20 ms.
Re-probe: **0/320 overruns** (worst case uses ~half the tiny budget).
Lesson: MW-0.1's 0/58 was luck of small samples at friendlier clocks;
low-clock behavior is now explicitly tested (`tools/time_probe.py` pattern,
unit budgets in `tests/test_agent.py`).

**Numba decision: rejected for MW-0.2.** No remaining hotspot satisfies
the gate (numerical, tight loop, no Python objects): movegen is
python-chess objects, eval was already 2.8x'd in pure Python, TT/push-pop
are dict/object code. A JIT would only add init risk for no measured win.

**Simplifications after measurement (behavior-neutral, diff_eval-clean).**
Deleted 9 write-only instrumentation counters and their hot-loop passes,
7 dead legacy eval functions, the `_opt` suffixes, and the vacuous
black-PST identity table. Net vs MW-0.1: eval file shorter in API surface,
search hot path strictly leaner.

**Reliability after all changes:** 32/32 unit tests, ruff + mypy strict
clean (36 files), 500/500 fuzz @150 ms, timing probe 0/320, mate-in-1 and
tactical suite green, packaged zip verified (agent.py at root, versions/
and tools/ excluded by packaging globs).

### External calibration (offline sparring, nothing ships)

Official Stockfish (local binary, 1 thread, ~1.05M NPS bench) vs MW-0.2
(MW at 30 s + 0.3 s rapid, fresh engine per game, alternating colours).
- Weak (Skill Level 2, 0.1 s/move): **2.0/4 (50%)**, +1 =0 -1 each colour.
- Intermediate (Skill Level 12, 0.2 s/move): **0.5/4 (12.5%)**, one draw.
- Zero illegal/crash/flag in all 8 games.
Reading: MW-0.2 splits with weak-club play and is outgunned by strong-club
play at rapid TC. Competition TC (120 s + 0.5 s, ~4x thinking time) favors
deeper search and should read better than this rapid calibration.
