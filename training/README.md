# MilkyWay Evaluation Tuning & Training Provenance

This directory contains the offline parameter tuning and dataset generation pipeline for MilkyWay handcrafted evaluation (Phase M16).

Nothing in this directory ships with the competition submission (`submission.zip` strictly packages only the 9 root runtime engine files).

---

## 1. Provenance & Dataset Pipeline

### Position Sources & Sampling
- **Seed Origins**: 
  - Standard ECO opening variations (Ruy Lopez, Sicilian Scheveningen/Najdorf, French, Caro-Kann, Queen's Gambit Declined, King's Indian, English, Reti).
  - Curated 40-position benchmark suite (`tools/benchmark_positions.py`) spanning openings, quiet middlegames, closed structures, tactical positions, and technical endings.
- **Game Rollouts**: Semi-random rollouts with tactical capture/check bias from seed openings.
- **Sampling Interval**: Sampled every 4–8 plies between ply 6 and 80 to prevent near-identical consecutive positions.
- **Exclusions**: Terminal checkmates, invalid FENs, and positions with immediate king captures are excluded.

### Deduplication
- **Stable Identity**: Canonical 4-tuple key: `piece_placement side_to_move castling_rights en_passant_square`. Halfmove and fullmove counters are disregarded for evaluation deduplication.
- **Dataset Size**: 25,000 unique positions collected across opening (12.4%), middlegame (46.3%), and endgame (41.2%) phases (average game phase 10.1 / 24).

---

## 2. Stockfish Integration & Labelling

- **Interface**: Offline UCI via python-chess (`chess.engine.SimpleEngine`).
- **Path Resolution**: Configurable via `STOCKFISH_PATH` environment variable or `--stockfish-path` CLI option.
- **Fallback / Fixture Mode**: When no external Stockfish binary is present on the development machine, `label_positions.py` operates in a reproducible `--mock` mode combining baseline evaluation with shallow tactical adjustment, preventing environment lock-in.
- **Configuration**: 1 thread, 64 MB hash, fixed node budget (`DEFAULT_NODE_BUDGET = 25,000`) for reproducible search horizon.
- **Score Convention**: All scores are converted to canonical **White perspective centipawns**:
  $$\text{score\_white} = \begin{cases} +\text{score\_cp} & \text{if turn is White} \\ -\text{score\_cp} & \text{if turn is Black} \end{cases}$$
- **Clamping**: Extreme centipawn scores are clamped to $[-1500, +1500]$ cp.
- **Mates**: Forced mate flags and distances are stored separately; forced-mate positions are excluded from linear continuous regression.

---

## 3. Feature Extraction & Schema

- **Schema Version**: `1.0.0` (`extract_features.py`)
- **Dimensions**: 50 explainable linear features matching `constants.TUNABLE_PARAM_NAMES`.
- **Mathematical Form**:
  $$\text{score} \approx \sum_{i=1}^{50} \beta_i \cdot x_i + \text{fixed\_terms}$$
  where each MG term is weighted by $w_{mg} = \frac{\text{phase}}{24}$, each EG term by $w_{eg} = \frac{24 - \text{phase}}{24}$, mobility by $(0.7 w_{mg} + 0.3 w_{eg})$, and king safety by $(1.0 w_{mg} + 0.2 w_{eg})$.
- **Fixed Terms**: Piece-square table (PST) net contribution and nonlinear mop-up bonus.
- **Symmetry**: Verified exact sign negation under `board.mirror()` across all 50 features.

---

## 4. Train / Validation / Test Splitting

- **Leakage Prevention**: Grouped strictly by `source_game_id`. All positions originating from the same game rollout remain in the same split.
- **Ratios**: 80% train (20,037 positions), 10% validation (2,482 positions), 10% held-out test (2,481 positions).
- **Random Seed**: Fixed seed `42`.

---

## 5. Fitting Methodology & Optimization

- **Objective Functions**:
  1. **Ridge Regression**: Regularized toward the frozen `MW_0_2_EVAL` baseline vector $\beta_0$:
     $$\min_{\Delta \beta} \|X \Delta \beta - r_{\text{baseline}}\|_2^2 + \lambda \|\Delta \beta\|_2^2$$
  2. **Huber Robust Regression**: Iteratively Reweighted Least Squares (IRLS) with Huber cutoff $\delta = 25.0$ cp to suppress tactical label noise.
- **Implementation**: Pure NumPy linear algebra (`np.linalg.solve`). No external ML dependencies.
- **Bounds & Sanity**: Hard bounds preventing negative piece values, illogical material ranking (queen > rook > bishop >= knight > pawn), or positive king exposure bonuses.

---

## 6. Verification & Arena Results Summary

- **Feature Parity**: Differential testing against integer evaluation shows absolute difference $\le 3$ cp across 500 quiet positions.
- **Search Freeze**: Audited via `tools/verify_search_freeze.py` (bit-for-bit identical to `versions/mw_0_2`).
- **M16-huber-01 Metrics (Held-out Test Set, 2,481 positions)**:
  - MAE: 60.48 cp $\to$ 59.41 cp ($-1.07$ cp)
  - Median AE: 18.37 cp $\to$ 15.08 cp ($-3.29$ cp)
  - RMSE: 180.34 cp $\to$ 176.52 cp ($-3.82$ cp)
  - Sign Accuracy: 99.4% $\to$ 99.5%
- **Arena Screen vs MW-0.2 (20 paired games, 10 suite positions)**:
  - `M16-huber-01`: +7 =3 -10, score **42.5%** (rejected).
  - `KS-B` (King Safety Ablation): +9 =4 -7, score **55.0%**, search NPS +17.6% (10,132 $\to$ 11,913), eval speed +48.1% (14,065 $\to$ 20,837).
- **MW-0.3 Decision**: **Retain MW-0.2 as competition build.** While KS-B demonstrated positive screen results and speedups, M16-huber-01 parameter tuning did not convincingly beat MW-0.2, and promotion criteria require statistically significant superiority (>55% across 200+ games). MW-0.2 remains the standing release point.
