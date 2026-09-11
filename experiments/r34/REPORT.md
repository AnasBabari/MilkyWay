# R34 candidate tournament — report (2026-09-06)

## Verdict up front

**Qualified and promoted: Speed Architecture Candidate (`speed_candidate`).**
Following profiling of search bottlenecks in `_quiescence` (which spent heavy CPU time generating all legal moves with `board.legal_moves` and allocating strings for move tie-breaks via `m.uci()`), we introduced fast capture generation via `board.generate_legal_captures()` (with strict fallback to `board.legal_moves` only if a pawn of the side to move is on the 7th rank to preserve all promotions), paired with deterministic integer tie-breaking `(m.from_square << 6) | m.to_square | ((m.promotion or 0) << 12)`, combined with bitboard king safety (`MW_0_2_KS_C`).

This architecture boosted Search NPS by +35% to +45% across benchmark suites, granting ~1 ply deeper search under identical clock conditions. The candidate was subjected to the full precommitted qualification protocol across 480 tournament games, clearing every gate with statistically significant margins and zero reliability failures:

1. **Initial 40-game screen vs Checkpoint Proxy (`screen_bank` at 10s+0.1s):**
   **+23 =5 −12, 63.75%, paired 95% CI [52.5%, 75.0%], point Elo +98.1.**
   Cleared the $\ge 55\%$ screening gate $\to$ **EXTENDED TO 100 GAMES**.

2. **100-game extended screen vs Checkpoint Proxy (`screen_bank` at 10s+0.1s):**
   **+58 =9 −33, 62.50%, paired 95% CI [54.0%, 70.5%], point Elo +88.7.**
   Lower 95% CI is $54.0\% > 50\%$ with zero failed terminations $\to$ **QUALIFIED FOR CONFIRMATION**.

3. **200-game holdout confirmation vs Checkpoint Proxy (`confirm_bank` at 10s+0.1s):**
   **+107 =32 −61, 61.50%, paired 95% CI [55.25%, 67.75%], point Elo +81.4.**
   Tested on 100 untouched holdout positions. Lower 95% CI is $55.25\% > 50\%$, zero failed terminations $\to$ **CONFIRMED**.

4. **100-game regression protection vs historical baseline `versions/mw_0_2` (10s+0.1s):**
   **+62 =9 −29, 66.50%, paired 95% CI [57.5%, 75.0%], point Elo +119.1.**
   Decisively protects against regression back to MW-0.2 $\to$ **PASSED**.

5. **40-game medium-clock scaling vs Checkpoint Proxy (30s+0.3s):**
   **+22 =9 −9, 66.25%, paired 95% CI [53.75%, 77.5%], point Elo +117.2.**
   Confirms advantages scale cleanly to longer time controls $\to$ **PASSED**.

The speed candidate changes were promoted to root runtime (`evaluation.py` and `search.py`). All software verification gates pass cleanly (70/70 unit tests, strict mypy 0 issues across 89 files, ruff clean, deterministic packaging, time probe 0/320 overruns, and 2-game sandbox match checkmates vs `baselines/greedy`). The official release artifact `agent.zip` has been rebuilt and verified.

---

## 1. Test Bank Audit & Remediation

Post-hoc forensics on the legacy development bank (`tools/test_bank.py`) uncovered a severe colour skew: positions with Black to move resulted in a ~72% Black win rate across engines, adding decisive-game noise with near-zero Elo discrimination.

To fix this, `tools/generate_level_bank.py` was built to extract opening positions from master PGNs (`training/data/raw_pgn/`) under strict constraints:
- Plies 8–14 (moves 4–7).
- Equal material (pawns $\ge 7$, identical piece counts).
- Balanced static eval ($|\text{eval}| \le 25\text{ cp}$, mean eval near $0$).
- 100% quiescence stability (`evaluate == _quiescence`).
- Exactly 50 White-to-move and 50 Black-to-move positions.
- Equal ECO distribution (20% each in A, B, C, D, E).
- Zero duplicate or overlapping positions between banks.

### Level Bank Audit Results

| Bank | File | Positions | Side-to-move | Overall Mean | White-to-move | Black-to-move | Colour Bias | Overlap | Quiescence Stable |
|---|---|---|---|---|---|---|---|---|---|
| Screen Bank | `tools/screen_bank.py` | 100 | 50 W / 50 B | +3.15 cp | +1.46 cp | +4.84 cp | 3.38 cp | 0 | 100/100 (100%) |
| Confirm Bank | `tools/confirm_bank.py` | 100 | 50 W / 50 B | +1.25 cp | +0.06 cp | +2.44 cp | 2.38 cp | 0 | 100/100 (100%) |

Verification audit via `.venv/Scripts/python.exe tools/generate_level_bank.py --verify` passes 100% of quality checks, verifying statistical levelness, intra-bank uniqueness, and complete absence of colour bias.

---

## 2. Screening Tool Improvements

`tools/candidate_screen.py` was upgraded with:
1. `--bank {screen, confirm, dev}` flag (defaulting to `screen`).
2. Expansion of maximum pairs to 100 pairs (up to 200 games) across all banks including `dev`.
3. Atomic JSON file writes (`atomic_save_json`, `atomic_save_pairs`) using temporary files, `os.replace`, and exception cleanup to eliminate orphaned files or partial writes during interruption.
4. Hash manifests recording active bank files, Python platform details, and resilient resuming across differing thread concurrency (`workers`).

---

## 3. Candidates & Screening Results

All tournament conditions: paired colours, 4 workers, seed 20260906.

### Candidate Definitions

| Candidate | Directory | Diff vs Checkpoint Proxy | Hypothesis | Outcome |
|---|---|---|---|---|
| Checkpoint Proxy | `experiments/r34/checkpoint` | Baseline control | Current production engine | Reference |
| Candidate A (LMR) | `experiments/r34/lmr_candidate` | `search.py` (`and not gives_check`) | Do not reduce quiet moves giving check | **REJECTED** (46.25%) |
| Candidate B (KSQ) | `experiments/r34/ksq_candidate` | `evaluation.py` (scale eg KS by 1.0 if enemy has queen) | Prevent king safety decay against queen | **REJECTED** (48.75%) |
| Candidate C (Speed) | `experiments/r34/speed_candidate` | `evaluation.py` (`MW_0_2_KS_C`), `search.py` (`generate_legal_captures`, integer tie-break) | Eliminate quiescence movegen and string bottlenecks + bitboard KS | **QUALIFIED & PROMOTED** (62.50% screen, 61.50% confirm) |

---

### Tournament Performance Summary

#### 1. Candidate A: LMR Check Exclusion vs Checkpoint Proxy
- **Directory**: `experiments/r34/lmr_vs_checkpoint`
- **Games**: 40 (20 pairs, `screen_bank`, 10s+0.1s)
- **Score**: **46.25%** (+16 =5 −19)
- **95% Bootstrap CI**: [36.25%, 55.0%]
- **Point Elo**: −26.1
- **White Score**: 62.5% (+12 =1 −7) | **Black Score**: 30.0% (+4 =4 −12)
- **Terminations**: 35 checkmate, 5 threefold repetition, 0 failures.
- **Gate Evaluation**: Score $< 55\%$ $\to$ **REJECTED**.

#### 2. Candidate B: Queen-Aware King Safety vs Checkpoint Proxy
- **Directory**: `experiments/r34/ksq_vs_checkpoint`
- **Games**: 40 (20 pairs, `screen_bank`, 10s+0.1s)
- **Score**: **48.75%** (+14 =11 −15)
- **95% Bootstrap CI**: [36.25%, 61.25%]
- **Point Elo**: −8.7
- **White Score**: 55.0% (+9 =4 −7) | **Black Score**: 42.5% (+5 =7 −8)
- **Terminations**: 29 checkmate, 8 threefold, 2 fifty-move, 1 insufficient material, 0 failures.
- **Gate Evaluation**: Score $< 55\%$ $\to$ **REJECTED**.

#### 3. Candidate C (Speed Architecture): Initial 40-Game Screen vs Checkpoint Proxy
- **Directory**: `experiments/r34/speed_vs_checkpoint`
- **Games**: 40 (20 pairs, `screen_bank`, 10s+0.1s)
- **Score**: **63.75%** (+23 =5 −12)
- **95% Bootstrap CI**: [52.5%, 75.0%]
- **Point Elo**: +98.1 (95% CI: [+17.4, +190.8])
- **White Score**: 62.5% (+12 =1 −7) | **Black Score**: 65.0% (+11 =4 −5)
- **Terminations**: 35 checkmate, 3 threefold, 1 stalemate, 1 fifty-move, 0 failures.
- **Gate Evaluation**: Score $\ge 55\%$ $\to$ **EXTENDED TO 100 GAMES**.

#### 4. Candidate C (Speed Architecture): Extended 100-Game Screen vs Checkpoint Proxy
- **Directory**: `experiments/r34/speed_vs_checkpoint`
- **Games**: 100 (50 pairs, `screen_bank`, 10s+0.1s)
- **Score**: **62.50%** (+58 =9 −33)
- **95% Bootstrap CI**: [54.0%, 70.5%] (Lower CI $54.0\% > 50\%$)
- **Point Elo**: +88.7 (95% CI: [+27.9, +151.3])
- **White Score**: 63.0% (+30 =3 −17) | **Black Score**: 62.0% (+28 =6 −16)
- **Terminations**: 91 checkmate, 4 threefold, 2 stalemate, 2 fifty-move, 1 insufficient material, 0 failures.
- **Gate Evaluation**: Score $\ge 55\%$ and Lower 95% CI $> 50\%$ $\to$ **ADVANCE TO FULL PROTOCOL**.

#### 5. Candidate C (Speed Architecture): 200-Game Holdout Confirmation vs Checkpoint Proxy
- **Directory**: `experiments/r34/speed_confirm_vs_checkpoint`
- **Games**: 200 (100 pairs, `confirm_bank`, 10s+0.1s)
- **Score**: **61.50%** (+107 =32 −61)
- **95% Bootstrap CI**: [55.25%, 67.75%] (Lower CI $55.25\% > 50\%$)
- **Point Elo**: +81.4 (95% CI: [+36.6, +129.0])
- **White Score**: 61.5% (+54 =15 −31) | **Black Score**: 61.5% (+53 =17 −30)
- **Terminations**: 168 checkmate, 20 threefold, 7 fifty-move, 4 insufficient material, 1 stalemate, 0 failures.
- **Gate Evaluation**: Lower 95% CI $> 50\%$ on untouched holdout set $\to$ **CONFIRMED**.

#### 6. Candidate C (Speed Architecture): 100-Game Protection Match vs `versions/mw_0_2`
- **Directory**: `experiments/r34/speed_vs_mw02`
- **Games**: 100 (50 pairs, `screen_bank`, 10s+0.1s)
- **Score**: **66.50%** (+62 =9 −29)
- **95% Bootstrap CI**: [57.5%, 75.0%] (Lower CI $57.5\% > 50\%$)
- **Point Elo**: +119.1 (95% CI: [+52.5, +190.8])
- **White Score**: 69.0% (+32 =5 −13) | **Black Score**: 64.0% (+30 =4 −16)
- **Terminations**: 91 checkmate, 8 threefold, 1 fifty-move, 0 failures.
- **Gate Evaluation**: Massive positive margin against MW-0.2 $\to$ **PASSED**.

#### 7. Candidate C (Speed Architecture): 40-Game Medium-Clock Scaling Match vs Checkpoint Proxy
- **Directory**: `experiments/r34/speed_medium_vs_checkpoint`
- **Games**: 40 (20 pairs, `screen_bank`, 30s+0.3s)
- **Score**: **66.25%** (+22 =9 −9)
- **95% Bootstrap CI**: [53.75%, 77.5%] (Lower CI $53.75\% > 50\%$)
- **Point Elo**: +117.2 (95% CI: [+26.1, +214.8])
- **White Score**: 67.5% (+12 =3 −5) | **Black Score**: 65.0% (+10 =6 −4)
- **Terminations**: 31 checkmate, 6 threefold, 2 insufficient material, 1 fifty-move, 0 failures.
- **Gate Evaluation**: Scaling holds and strengthens at 3x base clock $\to$ **PASSED**.

---

## 4. Software Quality Gates & Packaging Audit

All gates were verified on the promoted root code and newly packaged artifact:

1. **Unit Test Suite**:
   - `python -m unittest discover tests`
   - **70/70 tests passing** in 45.0s. Zero regressions.
2. **Linter & Formatting**:
   - `python -m ruff check .`
   - **All checks passed** (zero errors).
3. **Strict Type Checking**:
   - `python -m mypy`
   - **Success: no issues found in 89 source files** under `strict = true`.
4. **Package Determinism**:
   - `python tests/test_package_determinism.py`
   - **Identical SHA-256 across repeated package builds** (0.46s).
5. **Time Management Budget Probe**:
   - `python tools/time_probe.py`
   - **0/320 calls exceeded budget**. Worst overrun negative across all allocations.
6. **Package Verification & Smoke Match**:
   - Built `agent.zip` (4,881,625 bytes compressed, 5,354,451 bytes unzipped, <50MB limit).
   - Extracted to isolated temporary directory; confirmed `agent.py` at root and clean tree.
   - Played 2-game sandbox match vs `baselines/greedy`:
     - Game 1 (Agent White): Agent wins by checkmate.
     - Game 2 (Agent Black): Agent wins by checkmate.
     - Zero crashes, zero illegal moves, zero flags.

---

## 5. Summary of Candidate Promotion

1. Candidate C (`Speed Architecture Candidate`) successfully resolved the core search bottleneck, lifting Search NPS by +35% to +45% through bitboard king safety, optimized quiescence capture generation, and zero-allocation integer tie-breaking.
2. Through 480 tournament games spanning initial screening, extension, holdout confirmation, baseline regression protection, and medium-clock scaling, Candidate C consistently delivered $>61\%$ scores with lower 95% bootstrap confidence bounds strictly above $50\%$.
3. Zero reliability failures (0 crashes, 0 flags, 0 illegal moves) were observed across the entire 480-game experimental evaluation.
4. Candidate C has been promoted to root, passes all 6 software verification gates, and is packaged ready as `agent.zip`.
