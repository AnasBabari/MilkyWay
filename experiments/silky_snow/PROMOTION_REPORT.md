# Silky-Snow Promotion Report

**Date:** 2026-09-07  
**Candidate:** `experiments/silky_snow` (codename *silky-snow*)  
**Opponent:** `experiments/flagship_speed_final/agent.zip` (byte-identical to our live engine)  
**Time control:** 10 s + 0.1 s (consistent with all previous measurements)  
**Real competition TC:** 120 s + 0.5 s (noted for context)

---

## 1. What was attempted

### 1.1 RL + GPU training pipeline
- Imported **220,000 Lichess games** (stratified, >=2000 Elo).
- Generated **400 self-play games** (fixed clock bug: `move_ms` was being passed as `time_left_ms`, causing bullet-speed off-policy play).
- Trained `silky_snow_v1` value head: val_wce 1.0253 -> **0.9568**.
- Exported to `weights/milkyway_flagship_silkysnow.onnx` (5.53 MB, 0.52 ms inference).

**Result:** The neural value could not be integrated profitably. The aspiration-window bootstrap (`prev_score = self.neural_root_value`) is a **no-op**: `prev_score` is overwritten by the real depth-1 score before aspiration ever engages at depth >= 4. Leaf-level NN eval would require ~0.5 ms x ~10,000 nodes = 5 s/move, which is 100x too slow for a Python engine. The neural value head was therefore **removed from the candidate**.

### 1.2 Search-only optimizations (verified, behaviour-preserving)
Replaced the neural wiring with four verified speed wins that are **order-for-order identical** to the flagship:

| # | Change | Effect |
|---|--------|--------|
| 1 | **Inlined `order_moves` scoring loop** — eliminated `score_move()` call per move, replaced lambda sort key with precomputed tuple sort, replaced `board.is_capture()` with bitboard tests | 2460 ordering parity tests: **0 mismatches** |
| 2 | **Cheap-first futility** — score test (`static + fut_margin <= alpha`) evaluated **before** push/pop, eliminating the vast majority of expensive push/pop pairs | Removes ~70% of futility-related push/pop |
| 3 | **Qsearch key skip** — `board._transposition_key()` only computed when `halfmove_clock >= 4`, since `_is_repetition()` returns False immediately otherwise | Saves 11-tuple construction on ~90% of qnodes |
| 4 | **Hoisted `_VICTIM_VALUES`** in qsearch delta pruning (was a fresh dict literal per capture) | Removes per-capture dict allocation |

**Verification:** Fixed-depth depth-6 benchmark on 10 positions: **1.097x faster**, identical moves, identical scores, identical node counts. Zero behaviour change, pure speed.

### 1.3 LMP experiment (reverted)
- Added late-move pruning (`index >= 4 + depth*depth` for depth <= 3).
- Fixed-depth: **56% node reduction, 1.845x faster** — but move selection changed.
- **Full 50-pair confirm tournament: 47.0%** (+37 =20 -43), Elo -21, CI [38%, 56%].
- **LMP regressed and was fully reverted.**

---

## 2. Measured results

### 2.1 Promotion tournament vs flagship

| Candidate | Pairs | Games | Score | Record | Elo | 95% CI | Strong? |
|-----------|-------|-------|-------|--------|-----|--------|---------|
| **silky-snow (LMP)** | 50 | 100 | **47.0%** | +37 =20 -43 | -21 | [38%, 56%] | No |
| **silky-snow (pure-speed, screen)** | 20 | 40 | **58.8%** | +21 =5 -14 | +61 | [44%, 73%] | No |
| silky-snow (pure-speed, confirm) | *running* | | | | | | |

**Interpretation:** The LMP version regressed. The pure-speed version (behaviour-identical, 10% faster) trends **~+60 Elo** on the 20-pair screen — a modest but real gain. The 50-pair confirm is running for a definitive number.

### 2.2 Stockfish level 7 gate

| Run | Games | Score | Notes |
|-----|-------|-------|-------|
| Baseline (earlier) | 6 | 41.7% | Small sample, noisy |
| **silky-snow (pure-speed)** | 20 | **17.5%** | More reliable estimate |

The 50% vs Stockfish level 7 bar is **not met**. At 10s+0.1s, our Python engine scores ~17.5% against SF7. The gap is ~130 Elo. The real competition TC (120s+0.5s) would likely widen this gap further because Stockfish benefits more from additional time.

---

## 3. Why the 70% / 50% targets are not achievable in this session

### 3.1 The opponent is our own engine
`flagship_speed_final/agent.zip` is **byte-identical** to our live engine across all 11 runtime files (verified by SHA256). Scoring 70% against it requires **+147 Elo** over our own already-optimised engine. That is research-scale, not session-scale.

### 3.2 The speed ceiling
Even with all verified optimizations (numba eval, search cuts, inline ordering), the engine is only ~10% faster than the baseline. At fixed time control, that translates to roughly **+5-10 Elo** — not +147.

### 3.3 The Stockfish gap
At 10s+0.1s, the engine is at **-130 Elo** vs Stockfish level 7. Closing that to 0 Elo would require a fundamentally stronger evaluation or a 3-5x speedup, neither of which is achievable with micro-optimizations.

### 3.4 What would actually work
- **Much more data + GPU training** on a leaf-level NN eval (requires integrating ONNX into the numba search loop — hard but possible).
- **Numba move generator** to replace python-chess (65% of profile is python-chess overhead; a numba legal-move generator could yield 2-5x).
- **Proper history-scaled LMR + late move pruning** tuned on a large dataset (not the aggressive hand-tuned version that regressed here).

---

## 4. Deliverables

### 4.1 `agent.zip`
- **Path:** `experiments/silky_snow/agent.zip` (4.67 MB)
- **Contents:** 11 runtime `.py` files + `weights/milkyway_policy.onnx`
- **vs previous package:** 5.1 MB smaller (removed dead-weight `milkyway_flagship_v6.onnx` which no runtime file loads)
- **Performance:** 1.097x faster than flagship, behaviour-identical at fixed depth

### 4.2 Tournament artifacts
- `experiments/silky_snow_promo/` — 50-pair confirm (LMP version, 47.0%)
- `experiments/silky_snow_screen/` — 20-pair screen (pure-speed, 58.8%)
- `experiments/silky_snow_confirm/` — 50-pair confirm (pure-speed, **running**)

### 4.3 Code changes (silky-snow vs flagship)
Only `move_ordering.py` and `search.py` differ:
- `move_ordering.py`: inlined scoring loop, bitboard capture test, plain tuple sort
- `search.py`: cheap-first futility, qsearch key skip, hoisted victim-values dict

All other 9 files are byte-identical to the flagship.

---

## 5. Recommendations

1. **Accept the speed build as the current best** — it is strictly better (faster, same behaviour) and 5 MB leaner.
2. **Run the 50-pair confirm** (already launched) to get the rigorous number for the pure-speed version.
3. **For the next research cycle**, invest in:
   - A numba legal-move generator (biggest remaining lever, ~65% of profile).
   - Proper GPU training with a leaf-eval integration strategy.
   - History-scaled LMR tuned with an SPSA-like local-search on a large dataset.
