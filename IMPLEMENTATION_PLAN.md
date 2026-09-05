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
- [ ] M15 — Profiling / Numba optimisation (only if measured end-to-end win; eval 5.2k/s baseline recorded)
- [ ] M16 — Classical evaluation tuning (offline engine-labelled regression, ship coefficients only)
- [ ] M17 — Optional learned evaluation / policy (only if stronger than M16 in arena)
- [x] M18 (partial) — Production hardening: 32 unit tests, 200-position fuzz clean, gate green, zip 57 KB verified

Next: M15 profiling/Numba decision, then M16 eval tuning, then larger arenas (100+ games MW-0.1 vs MW-0.2 for every later change).

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
