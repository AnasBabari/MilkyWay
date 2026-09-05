# MilkyWay — Implementation Plan

Milestone tracker for the AI Chessathon competition engine.
Competition: 120s + 0.5s, 1 CPU core, 2 GB RAM, 90s init, 50 MB zip.
Submission API: `get_move(fen, time_left_ms) -> uci`.

- [x] M0 — Baseline (unmodified starter, random mover)
- [x] M1 — Module architecture (`agent.py` thin + root engine modules)
- [x] M2 — Handcrafted tapered evaluation (material, PST, pawn, rook, mobility, king safety, mop-up)
- [x] M3 — Alpha-beta negamax (mate-distance scores, push/pop integrity)
- [x] M4 — Iterative deepening (keep last completed iteration)
- [x] M5 — Robust time manager (soft/hard deadlines, emergency mode)
- [x] M6 — Transposition table (EXACT/LOWER/UPPER, generations, cross-move persistence)
- [x] M7 — Move ordering (TT move, promotions, MVV-LVA captures, killers, history)
- [x] M8 — Quiescence search (stand-pat, captures/promotions, evasions, qply cap)
- [x] M9 — Killers + history heuristic
- [x] M10 — Principal Variation Search
- [x] M11 — Aspiration windows
- [x] M12 — Late Move Reductions
- [x] M13 — Null-move pruning (conservative, zugzwang-aware)
- [x] M14 — Futility / reverse futility / check extensions (conservative)
- [x] M15 — Profiling / Numba optimisation: 2.09x search NPS measured;
  Numba explicitly rejected (no qualifying hotspot); see BENCHMARKS.md
- [ ] M16 — Classical evaluation tuning (offline engine-labelled regression, ship coefficients only)
- [ ] M17 — Optional learned evaluation / policy (only if stronger than M16 in arena)
- [x] M18 (partial) — Production hardening: 32 unit tests, 500-position fuzz
  clean, timing probe 0/320, gate green, zip verified, 100-game A/B recorded

MW-0.2 tagged: bitboard eval + lean ordering + O(1) TT + low-clock flag fix.
A/B: MW-0.2 vs MW-0.1 96.0% over 100 games. Opponent snapshots live in
versions/ (mw_0_1 faithful to 772e9a5, verified). Paired FEN-bank arena
(tools/paired_arena.py, 40 positions x2 colours) is the default A/B for M16:
tuned-eval candidates must beat MW-0.2 with search code identical.

## Order of work

correctness → reliability → search strength → speed → advanced eval → ML.

No neural network before the classical engine passes strength + reliability gates.
Every strength change is judged by `old MilkyWay vs new MilkyWay` arenas, not by 2-game anecdotes.

## Strength gates

- random → greedy → minimax → numba → previous MilkyWay
- quick screen: 20–50 games; serious: 100–500 games, alternating colours, fixed TC

## Reliability gates (candidate must satisfy)

- zero illegal moves / crashes / flags / missing imports / board corruption
- `make gate` clean (ruff, mypy, 2 smoke games)
- random-position fuzzing + fast reliability games
- packaged zip verified: `agent.py` at root, all root modules present, <50 MB, no native binaries
