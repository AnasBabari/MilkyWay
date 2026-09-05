# MilkyWay — Implementation Plan

Milestone tracker for the AI Chessathon competition engine.
Competition: 120s + 0.5s, 1 CPU core, 2 GB RAM, 90s init, 50 MB zip.
Submission API: `get_move(fen, time_left_ms) -> uci`.

- [x] M0 — Baseline (unmodified starter, random mover)
- [ ] M1 — Module architecture (`agent.py` thin + root engine modules)
- [ ] M2 — Handcrafted tapered evaluation (material, PST, pawn, rook, mobility, king safety, mop-up)
- [ ] M3 — Alpha-beta negamax (mate-distance scores, push/pop integrity)
- [ ] M4 — Iterative deepening (keep last completed iteration)
- [ ] M5 — Robust time manager (soft/hard deadlines, emergency mode)
- [ ] M6 — Transposition table (EXACT/LOWER/UPPER, generations, cross-move persistence)
- [ ] M7 — Move ordering (TT move, promotions, MVV-LVA captures, killers, history)
- [ ] M8 — Quiescence search (stand-pat, captures/promotions, evasions, qply cap)
- [ ] M9 — Killers + history heuristic
- [ ] M10 — Principal Variation Search
- [ ] M11 — Aspiration windows
- [ ] M12 — Late Move Reductions
- [ ] M13 — Null-move pruning (conservative, zugzwang-aware)
- [ ] M14 — Futility / reverse futility / check extensions (conservative)
- [ ] M15 — Profiling / Numba optimisation (only if measured end-to-end win)
- [ ] M16 — Classical evaluation tuning (offline engine-labelled regression, ship coefficients only)
- [ ] M17 — Optional learned evaluation / policy (only if stronger than M16 in arena)
- [ ] M18 — Production hardening (fuzzing, reliability gates, packaging)

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
