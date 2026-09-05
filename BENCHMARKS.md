# MilkyWay — Benchmarks

All results are `agent (./MilkyWay) vs opponent`, alternating colours (even game = agent White).
Time controls noted per row. Harness: `harness/arena.py` / `harness/play.py`.

> [!WARNING] **LEGACY HARNESS NOTICE (pre-upstream-91f70e5, 300-ply material adjudication)**
> Historical benchmarks recorded prior to commit `91f70e54be07e1bf56311962044a08b822c3af50` used the 300-ply cap with material adjudication.
> Any game terminated by `adjudication` is obsolete as a platform-equivalent result under current platform rules (which enforce a 600-ply draw cap).
> Checkmate, threefold repetition, 50-move, stalemate, crash, and illegal results remain valid historical reference points subject to the new flag-insufficient-material rule.

## M0 — Unmodified starter baseline (random mover, 2026-09-05, local Windows, uv sync)

*Harness: LEGACY HARNESS (pre-upstream-91f70e5, 300-ply material adjudication)*

Environment: Python 3.14.5 (local; platform is 3.12), chess 1.11.2, numpy 2.5.2,
numba 0.67.0, torch 2.13.0+cpu, onnxruntime 1.29.0. Local machine (not EPYC 9V74).

| Date | Matchup | Games | TC | Score | W/D/L | Terminations | Notes |
|------|---------|-------|----|-------|-------|--------------|-------|
| 2026-09-05 | starter(random) vs baselines/random | 2 | 5s+0.1s(?) `--base-ms 5000` | 50.0% | +1 =0 -1 | adjudication 2 | `make gate` smoke: ruff OK, mypy OK (obsolete termination under 600-ply draw cap) |
| 2026-09-05 | starter(random) vs baselines/greedy | 20 | 10s+0.1s (arena default) | 10.0% | +0 =4 -16 | stalemate 4, checkmate 16 | matches README (~10%) |
| 2026-09-05 | starter(random) vs baselines/minimax | 6 | 10s+0.1s | 8.3% | +0 =1 -5 | checkmate 5, threefold 1 | expected: random loses |
| 2026-09-05 | starter(random, White) vs greedy(Black), single `harness.play` | 1 | 120s+0.5s | draw | =1 | threefold_repetition | sanity: full-TC game finishes cleanly |

README reference (upstream, tiny samples): random vs greedy 10.0% (20 games, 10s+0.1s);
greedy vs minimax 0.0% (6 games, 120s+0.5s); numba vs minimax 66.7% (+2 =4 -0, 6 games).

No crashes / illegal moves / flags in M0 baseline runs.

## Milestone results (append below)

### MW-0.1 — first competition engine (2026-09-05, local Windows, uv sync)

*Harness: LEGACY HARNESS (pre-upstream-91f70e5, 300-ply material adjudication)*

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

*Harness: LEGACY HARNESS (pre-upstream-91f70e5, 300-ply material adjudication)*

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

### M16 — Offline Handcrafted Evaluation Tuning (2026-09-05, local Windows, uv sync)

*Harness: LEGACY HARNESS (pre-upstream-91f70e5, 300-ply material adjudication)*

**Rule for the phase**: FREEZE SEARCH → BUILD DATASET → EXTRACT EXPLAINABLE FEATURES →
LABEL OFFLINE → FIT COEFFICIENTS → VALIDATE OUT OF SAMPLE → PLAY PAIRED ARENAS → KEEP OR REJECT.

**Search Freeze Guard**:
- Non-evaluation modules (`agent.py`, `engine.py`, `engine_types.py`, `move_ordering.py`, `search.py`, `time_manager.py`, `transposition.py`) audited by `tools/verify_search_freeze.py` and `tests/test_search_freeze.py`.
- Result: **Bit-for-bit identical to `versions/mw_0_2`** (all SHA-256 hashes match).
- Fixed-depth search parity: 51,879 nodes, 123,116 qnodes, 174,995 total nodes (10,132 NPS) identical between MW-0.2 and parameter-refactored evaluator using `MW_0_2_EVAL`.

**Evaluation Refactoring & Parity Gate**:
- Evaluation constants codified into immutable `EvalParameters` dataclass.
- Baseline preserved as `MW_0_2_EVAL`.
- Differential evaluation gate (`tools/diff_eval.py`) across **10,000 legal random positions**: **0 mismatches (100% exact integer equality)**.

**Feature Extraction & Canonical Representation**:
- 50 explainable first-stage features matching `TUNABLE_PARAM_NAMES` (material MG/EG, mobility, pawn structure, rank 2..7 passed pawns, rook activity, king safety).
- All features strictly canonical White-perspective.
- Verified exact colour symmetry on `board.mirror()` across all 50 features and evaluation scores (`tests/test_feature_extraction.py`).
- Linear reconstruction fidelity: within ±1..3 cp of integer evaluation on quiet positions.

**Dataset & Provenance**:
- 25,000 unique legal positions collected across public ECO openings and curated benchmark suite rollouts.
- Deduplicated by 4-tuple canonical board key (piece placement, turn, castling, en-passant).
- Distribution: 12.4% opening (phase >= 20), 46.3% middlegame (8 <= phase < 20), 41.2% endgame (phase < 8); average phase 10.1 / 24.
- Split strictly by `source_game_id` (zero position leakage between splits):
  - Train: 20,037 positions (80%)
  - Validation: 2,482 positions (10%)
  - Held-out Test: 2,481 positions (10%)
- Labeled with canonical White-perspective centipawns, forced mates flagged and isolated, scores clamped to [-1500, +1500] cp.

**Fitting Experiments**:
- `M16-ridge-01`: Ridge regression regularized toward `MW_0_2_EVAL` with standardized feature scaling.
- `M16-huber-01`: Robust Huber regression (delta = 25.0 cp, lambda = 5000.0) via Iteratively Reweighted Least Squares (IRLS) with feature standardization (scales = max(std, 1e-4)) and mobility sanity lower bounds.

**Held-out Test Metrics (2,481 positions)**:
| Metric | MW-0.2 Baseline | M16-huber-01 Tuned | Delta |
|--------|-----------------|--------------------|-------|
| MAE | 60.48 cp | **59.23 cp** | **-1.25 cp** |
| Median AE | 18.37 cp | **14.73 cp** | **-3.64 cp** |
| RMSE | 180.34 cp | **175.81 cp** | **-4.53 cp** |
| Sign Accuracy | 99.4% | **99.5%** | **+0.1%** |
| Pearson r | 0.9833 | **0.9841** | **+0.0008** |
| Pairwise Order Acc | 99.4% | 99.4% | +0.0% |
| Middlegame MAE | 93.8 cp | **91.1 cp** | **-2.7 cp** |

**Neutral Test Bank (Section 31)**:
- Generated in `tools/test_bank.py` (`BANK_VERSION = "1.0.0"`).
- Contains 200 legal, near-balanced positions ($|\text{eval}| \le 45$ cp) sampled across openings (50), middlegames (100), and endgames (50) to eliminate opening bias in paired arenas.

**King Safety Ablation & Microbenchmark (Section 32)**:
- Profiling revealed king-safety attack checks (9 `is_attacked_by` calls per king) consume ~18% of eval runtime.
- Evaluated KS-A (baseline), KS-B (simplified: pawn shield, open files near king, queen proximity), and KS-C (bitboard king-zone attacks):
  - Standalone isolated KS: KS-A 97,832 call/s | KS-B 593,930 call/s (6.07x) | KS-C 489,356 call/s (**5.00x speedup**).
  - Full static eval throughput: KS-A 14,546 eval/s | KS-B 20,421 eval/s (+40.4%) | KS-C 19,861 eval/s (**+36.5% speedup**).
  - KS-C bitboard calculation `((enemy_attacks_bb | patt) & kzone).bit_count()` matches KS-A attack counts 98.6% of the time (max diff 1) with zero `is_attacked_by` calls.

**Paired Candidate Arena Results (vs frozen MW-0.2 control, FAST TC 500ms+50ms, neutral bank)**:
| Candidate | Games | Score | W/D/L | Terminations | Notes |
|-----------|-------|-------|-------|--------------|-------|
| KS-C ablation | 20 | **57.5%** | +11 =1 -8 | checkmate 17, threefold 2, 50-move 1 | Evaluator speedup (+36.5%) gives positive screen |
| M16-huber-01 screen | 20 | **62.5%** | +12 =1 -7 | checkmate 18, threefold 2 | Standardized fit with sound mobility bounds |
| M16-huber-01 extended | 100 | **53.0%** | +48 =10 -42 | checkmate 89, threefold 8, 50-move 3 | Positive win delta (+6), but fails >55% gate |

**MW-0.3 Decision**:
- **REJECT promotion; RETAIN MW-0.2 as competition build (`ACTIVE_PARAMS = MW_0_2_EVAL`).**
- Per Section 38 promotion criteria: candidate must convincingly clear >55% over a substantial sample. While M16-huber-01 achieved a positive score (53.0%, +6 game margin), it did not clear the 55% threshold. KS-C (+36.5% eval speed, 57.5% screen) and standardized Huber tuning provide sound foundations, but MW-0.2 remains the standing competition release.
- Production engine code remains 100% bit-for-bit identical to MW-0.2.

### AI Chessathon platform validation — 2026-09-05

*Harness: LEGACY HARNESS (pre-upstream-91f70e5, 300-ply material adjudication)*

Build: MW-0.2 validated candidate

- Build: PASS
- Uncompressed package: 71,835 bytes
- Init: 0.7 s as White / 0.5 s as Black
- White smoke: PASS, adjudication (obsolete termination under 600-ply draw cap)
- Black smoke: PASS, adjudication (obsolete termination under 600-ply draw cap)
- Slowest move: 12.0 s
- Illegal moves: 0
- Crashes: 0
- Flags: 0
- Overall result: VALID

### M17.5 — Forensics, Root Policy, and TM-B Fixes (2026-09-05)

*Harness: LEGACY HARNESS (pre-upstream-91f70e5, 300-ply material adjudication)*

Match testing against previous frozen milestones (`versions/mw_0_1` and `versions/mw_0_2`).
Time control: 10s base + 0.1s increment, alternating colours.

| Matchup | Games | Score | W/D/L | Terminations | Notes |
|---------|-------|-------|-------|--------------|-------|
| Candidate vs MW-0.1 | 2 | **100.0%** | +2 =0 -0 | checkmate 2 | Smoke gate |
| Candidate vs MW-0.1 | 10 | **95.0%** | +9 =1 -0 | checkmate 9, threefold 1 | Dominant win rate vs MW-0.1 |
| Candidate vs MW-0.2 | 2 | **100.0%** | +2 =0 -0 | checkmate 2 | Smoke gate |
| Candidate vs MW-0.2 | 10 | **55.0%** | +5 =1 -4 | checkmate 9, threefold 1 | Positive score vs frozen MW-0.2 |

## Upstream Rules Sync & Post-91f70e5 Benchmarks (2026-09-05)

### AI Chessathon upstream rules update — 2026-09-05

- **Upstream commit:** `91f70e54be07e1bf56311962044a08b822c3af50` (`fix(harness): draw a capped game and a flag against a bare king`)
- **Old rules:**
  - 300-ply cap, material adjudication (`_adjudicate()`)
  - Flag fall is always a loss for mover
  - Cap checked `len(board.move_stack) >= 300` (ignored opening FEN ply count)
- **New rules:**
  - 600-ply cap, draw (`board.ply() >= 600 -> result="draw", termination="ply_cap"`)
  - Flag fall is a draw when opponent has insufficient mating material (`board.has_insufficient_material(not mover)`)
  - Cap checked `board.ply() >= 600` (opening FEN move number/turn properly contributes to cap)

### Provenance Classification:
- **Legacy harness (pre-upstream-91f70e5, 300-ply material adjudication):**
  M0, MW-0.1, MW-0.2, and M17.5 historical runs prior to commit `91f70e5`. Results terminated by `adjudication` are obsolete as platform-equivalent metrics.
- **New harness (post-upstream-91f70e5, 600-ply draw cap):**
  All subsequent benchmarks, long-game simulations, and candidate validations.

### Post-Sync Verification & Candidate Retest Benchmarks (New Harness)

| Date | Matchup | Games | TC | Score | W/D/L | Terminations | Notes |
|------|---------|-------|----|-------|-------|--------------|-------|
| 2026-09-05 | Candidate (Package) vs baselines/greedy | 2 | 5s+0.1s | 100.0% | +2 =0 -0 | checkmate 2 | Package gate smoke test on new harness |
| 2026-09-05 | Candidate vs versions/mw_0_2 | 10 | 10s+0.1s | 50.0% | +5 =0 -5 | checkmate 10 | Fresh candidate vs frozen MW-0.2 control |
| 2026-09-05 | Candidate (Policy ON) vs Policy OFF | 6 | 10s+0.1s | 41.7% | +2 =1 -3 | checkmate 5, threefold_repetition 1 | Root policy ON vs OFF ablation |
| 2026-09-05 | Candidate vs versions/mw_0_2 (Endgames) | 16 | 5s+0.1s | 46.9% | +4 =7 -5 | checkmate 9, insufficient_material 4, fifty_moves 2, threefold_repetition 1 | Paired 8 endgame positions under 600-ply cap |

### Long-Game Clock Trajectory Simulation (120s + 0.5s TC, 300 moves per side / 600 plies)
Simulated via `tools/simulate_long_game.py`:
- **Nominal (1.0x soft budget):**
  - Move 10: 97.86s
  - Move 25: 72.85s
  - Move 50: 45.51s
  - Move 100: 20.20s
  - Move 150: 11.55s
  - Move 200: 8.59s
  - Move 250: 7.58s
  - Move 295: 7.26s
  - Move 300: 7.24s (stable asymptotic equilibrium)
- **Overrun (1.2x soft budget):**
  - Move 10: 93.10s
  - Move 25: 64.20s
  - Move 50: 35.15s
  - Move 100: 11.94s
  - Move 150: 5.96s (enters emergency mode)
  - Move 200+: 5.95s (stable asymptotic equilibrium)
- **Heavy Stress (1.5x soft budget):**
  - Move 10: 86.30s
  - Move 25: 52.78s
  - Move 50: 23.05s
  - Move 100: 5.11s (enters emergency mode)
  - Move 150+: 4.76s (stable asymptotic equilibrium)

## M18 — Production Qualification Tournament & Statistical Protocol (2026-09-05)

*Harness: NEW HARNESS (post-upstream-91f70e5, 600-ply draw cap)*

Execution of the formal 15-amendment qualification protocol evaluating frozen candidate `MilkyWay RC1` (commit `e252106c3b4dc6d60b72e822673641c894be9d49`) against frozen control `versions/mw_0_2`.

### Protocol Setup & Audits:
- **Bank Stratification**: Deterministic split (`M18_SPLIT_SEED = 20260905`, Bank SHA-256 `505bdd4860bab9fc20c4b43ae38bafc1693e5d07ad758dacbd56d6ae0ec1fac1`) yielding two non-overlapping 100-pair sets (Screen and Confirmation), each exactly 25 opening, 50 middlegame, and 25 endgame pairs.
- **Bank Distribution Audit**: Fullmoves min 3, max 77, median 21; halfmove clock min 0, max 88, median 1; starting ply min 4, max 152, median 41. No near-cap positions (min 448 plies remaining vs 600-ply cap).
- **Packaging Determinism**: Bit-identical builds verified (`sha1 == sha2 == af55cb1777778141b0b1de26bb8c8c08445a5c59280c01fcdb152be3366de063`). Uncompressed payload 5,353,731 bytes (limit <50 MB). Extracted 2-game smoke: 100% checkmate wins.
- **Pre-tournament Software Gates**: `ruff check` PASS (clean repo-wide), `mypy` PASS (strict clean across all files), `tests` PASS (69/69 in 49.5s), time probe PASS (0/320 overruns), ONNX smoke PASS (median 0.51 ms latency, 18-plane input), 20-game arena vs `baselines/greedy` PASS (+20 =0 -0, 100% checkmates).
- **Rated Regressions (Gate 6)**: R20 (LarpMaxx) and R25 (Neomatica) unit tests PASS (4/4 in 41.1s).
- **Long-Game Live-Search Stress (Gate 0)**: 250 candidate decisions sustained live search under 120s+0.5s TC. Zero flags, zero crashes, zero illegals across all moves and 25 game completions; stable asymptotic clock equilibrium verified.

### Tournament & Ablation Results:

| Stage | Pairs / Games | TC | Score | W/D/L | 95% Bootstrap CI | Point Elo [95% CI] | Gate Status |
|---|---|---|---|---|---|---|---|
| Gate 1: Screen Set | 100 / 200 | 10s+0.1s | **52.0%** | +86 =36 -78 | [47.0%, 57.0%] | +13.9 [-20.9, +49.0] | PASS (cond. >=52%) |
| Gate 2: Holdout Confirmation | 100 / 200 | 10s+0.1s | **52.25%** | +90 =29 -81 | [47.75%, 57.0%] | +15.6 [-15.6, +49.0] | PASS (>50% req.) |
| Gate 3: Combined 400 (Exploratory) | 200 / 400 | 10s+0.1s | **52.125%** | +176 =65 -159 | [48.75%, 55.5%] | +14.8 [-8.7, +38.4] | **FAIL** (<55% target, CI spans neutral) |
| Gate 4: Policy ON vs Policy OFF | 20 / 40 | 10s+0.1s | **50.0%** | +18 =4 -18 | [35.0%, 65.0%] | 0.0 [-107.5, +107.5] | Neutral |
| TM-B vs TM-A Ablation | 20 / 40 | 10s+0.1s | **47.5%** | +16 =6 -18 | [36.25%, 58.75%] | -17.4 [-98.1, +61.4] | Control favored |
| Gate 5a: Medium TC Bridge | 20 / 40 | 30s+0.3s | **51.25%** | +18 =5 -17 | [38.75%, 63.75%] | +8.7 [-79.5, +98.1] | Positive |
| Gate 5b: Full TC Bridge | 10 / 20 | 120s+0.5s | **45.0%** | +7 =4 -9 | [30.0%, 57.5%] | -34.9 [-147.2, +52.5] | **FAIL** (direction reversal) |

### Stratified Performance Breakdown:
- **Colour Stratification (Combined 400)**:
  - White: 44.75% (+71 =37 -92)
  - Black: 59.50% (+105 =28 -67)
- **Phase Stratification (Combined 400)**:
  - Opening (50 pairs): 56.0% (+52 =8 -40)
  - Middlegame (100 pairs): 49.5% (+87 =24 -89)
  - Endgame (50 pairs): 53.5% (+37 =33 -30)
- **Pair Score Distribution (Combined 400, 200 pairs)**:
  - 2.0 (Double win): 23 pairs (11.5%)
  - 1.5 (Win + Draw): 22 pairs (11.0%)
  - 1.0 (Balanced split): 120 pairs (60.0%)
  - 0.5 (Loss + Draw): 19 pairs (9.5%)
  - 0.0 (Double loss): 16 pairs (8.0%)

### Reliability & Terminations (540 Total Games):
- Zero crashes, zero flags, zero illegal moves.
- Checkmate: 457 (84.6%)
- Threefold repetition: 47 (8.7%)
- Insufficient material: 17 (3.1%)
- Fifty moves: 13 (2.4%)
- Stalemate: 6 (1.1%)

### Promotion Gate Evaluation:
- `Gate 0 (Reliability)`: **PASS** (zero crashes, flags, or illegals across all matches).
- `Gate 1 (Screen Set)`: **PASS** (52.0% >= 52% conditional threshold).
- `Gate 2 (Untouched Holdout Confirmation)`: **PASS** (52.25% > 50% threshold).
- `Gate 3 (Combined 400 Games)`: **FAIL** (52.125% < 55.0% target; 95% CI [48.75%, 55.5%] includes neutral).
- `Gate 4 (Policy ON vs OFF)`: **PASS** (50.0% >= 50.0% threshold).
- `Gate 5 (Time Control Scaling)`: **FAIL** (Direction reversal at Full TC 120s+0.5s: 45.0% < 50.0%).
- `Gate 6 (Rated Regressions)`: **PASS** (R20 LarpMaxx & R25 Neomatica green).
- `Gate 7 (Packaging Audit)`: **PASS** (Deterministic SHA, payload <50MB, smoke verified).

### Final Promotion Decision:
**`REJECT_AND_RETAIN_MW02`**
MilkyWay RC1 demonstrates perfect execution reliability (zero crashes, zero flags, zero illegal moves over 540 tournament games and 250 candidate stress decisions) and preserves all historical regression benchmarks. However, it fails the primary promotion criteria:
1. It achieves only +14.8 Elo (52.1%) across the 400-game test bank, missing the >=55% promotion target, with a 95% paired bootstrap confidence interval [48.8%, 55.5%] that spans neutral.
2. In the full competition time-control bridge (120s+0.5s), candidate performance reverses direction to 45.0% (-34.9 Elo), indicating search efficiency and scaling deficits at deeper plies against MW-0.2.
Per the precommitted protocol, `RC1` is rejected for promotion, and `MW-0.2` is retained as the standing competition engine.



