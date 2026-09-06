# Rated Regression Suite: Round 25 (MilkyWay vs neomatica)

**Match ID**: `d5dff108-e205-45cc-9237-5c1491ea20a9`  
**Date**: 2026-09-05 16:21:16 UTC  
**Event**: AI Chessathon Rated Round 25  
**Opponent**: neomatica  
**Colour**: White  
**Opening**: Pirc Defence  
**Starting FEN**: `rnbq1rk1/ppp1ppbp/3p1np1/8/3PPB2/2N2N2/PPP1BPPP/R2QK2R b KQ - 5 6`  
**Model Version**: `MW-R25-POLICY` (Commit `0d3741f9c988d0c945d728b74e5b8d1d02bfaa8f`)  
**Base Architecture**: `chess_policy_student_64x4` ONNX via `weights/milkyway_policy.onnx`  

---

## Executive Summary & Attribution Verdict

The second-pass forensic re-audit with process-level environment isolation revealed a **critical causal attribution**:

1. **MW-0.2 Outperformed MW-R25-POLICY**:
   When run with strict environment isolation (`PYTHONPATH=versions/mw_0_2`), MW-0.2 diverged from the played moves on key turning points:
   - **Move 14**: MW-0.2 found **`14. Rc1!`** (+286 cp, Stockfish #1 move), while the policy engine played **`14. Bd2`** (+179 cp).
   - **Move 18**: MW-0.2 found **`18. g4!`**, completely avoiding the catastrophic blunder **`18. Ra1??`** (-552 cp).
   - **Move 20**: MW-0.2 found **`20. Ne6!`**, avoiding the immediate forced checkmate in 8 caused by **`20. Nxe4??`**.

2. **Policy Model Causal Regression**:
   The identical search code with root policy disabled (`R25-NOPOLICY`, `MILKYWAY_ROOT_POLICY=0`) matched MW-0.2:
   `R25-NOPOLICY` played `14. Rc1`, `18. g4`, and `20. Ne6`!
   This proves conclusively that the **learned policy move ordering poisoned the root search under time pressure**, actively demoting sound moves (`14. Rc1` was policy rank 27, `18. Qb3+` was rank 41) while hallucinating an unsound Greek Gift sacrifice (`Nxh7` rank 1 with 58%–88% probability across 8 consecutive plies).

---

## Structured Regression Records

### Record 1: Move 14 — Premature Advantage Liquidation (`14. Bd2` vs `14. Rc1`)

```yaml
id: R25_NEOMATICA_01
game: Round 25 vs neomatica
ply: 27
move_number: 14
fen: "5rk1/p2n1pbp/b5p1/6N1/P3NB2/2P5/1q3PPP/R2QK2R w KQ - 0 20"
model_version: MW-R25-POLICY (0d3741f)
played_move: f4d2 (Bd2)
best_move: a1c1 (Rc1)
cpl: 107
eval_before_cp: 286
eval_after_cp: 179
wdl_delta: -15% Win Probability
classification: POLICY_ORDERING
root_cause: >
  Policy net hallucinated 14. Nxh7? as rank 1 (p=0.6312).
  The correct active rook defense 14. Rc1! was demoted to rank 27 (p=0.00048).
  Under clock pressure (3.5s budget), search explored bad policy candidates and settled for Bd2.
  Both isolated MW-0.2 and R25-NOPOLICY found 14. Rc1 without the policy.
regression_expectation: >
  Engine must choose 14. Rc1 under >= 2.0s budget, preserving >= +250 cp advantage.
training_status: RATED_HOLDOUT
```

#### Detailed Context
- **Board State**: White has just pushed `12. dxe7` and `13. exf8=Q+`, winning material. Black's queen sits on `b2`, attacking the rook on `a1`. White's bishop on `f4` and knight on `e4` are active.
- **Stockfish MultiPV 5**:
  1. `14. Rc1!` (+286 cp): Dominates the c-file, traps Black's queen from escaping via c3/a2.
  2. `14. Bd6` (+212 cp)
  3. `14. Rb1` (+184 cp)
  4. `14. Bd2` (+179 cp): Passively retreats bishop, allowing Black's knight to activate (`14...Ne5!`).
- **Policy Distribution**:
  - #1 `Nxh7`: 63.12% (Logit 4.96) — Blunders piece
  - #2 `Ng3`: 10.84%
  - #3 `Nd2`: 6.86%
  - #27 `Rc1`: 0.05% (Logit -3.02) — Demoted to bottom tier!
- **Counterfactual Verdict**:
  - `MW-0.2`: Plays `14. Rc1`
  - `R25-NOPOLICY`: Plays `14. Rc1`
  - `MW-R25-POLICY`: Plays `14. Bd2`
  - **Verdict**: Proven policy regression.

---

### Record 2: Move 18 — The Decisive Collapse (`18. Ra1??` vs `18. Qb3+!` / `18. g4`)

```yaml
id: R25_NEOMATICA_02
game: Round 25 vs neomatica
ply: 35
move_number: 18
fen: "5rk1/p5bp/b5p1/5pN1/P3N3/2PnK3/q2B1PPP/1R1Q3R w - - 0 24"
model_version: MW-R25-POLICY (0d3741f)
played_move: b1a1 (Ra1??)
best_move: d1b3+ (Qb3+!) / g2g4 (g4)
cpl: 526
eval_before_cp: -26
eval_after_cp: -552
wdl_delta: Collapsed from 40% Draw to 0% Win / 100% Loss
classification: POLICY_ORDERING
root_cause: >
  The decisive blunder of the game. White's king is exposed on e3, but Black's queen on a2 is loose.
  Stockfish's tactical refutation is 18. Qb3+! forcing queen trade and neutralizing Black's attack.
  The policy net ranked Qb3+ at #41 (p=0.00025) and promoted 18. Nxh7 (p=0.5858).
  Under low clock (2.5s remaining allocation), search could not find Qb3+ or g4 and chose Ra1.
  Isolated MW-0.2 and R25-NOPOLICY both chose 18. g4, which holds the position.
regression_expectation: >
  Engine must choose 18. Qb3+ or 18. g4 and strictly reject 18. Ra1.
training_status: RATED_HOLDOUT
```

#### Detailed Context
- **Board State**: White's King is walked out to `e3`. Black has just played `17...f5!`, threatening `18...f4+` and opening lines against White's King.
- **Stockfish MultiPV 5**:
  1. `18. Qb3+!` (+25 cp): Decisive queen trade. `18...Qxb3 19. Rxb3 fxe4 20. Nxe4` leaves White with rook and knight vs bishop and pawns, equal/playable.
  2. `18. g4` (-38 cp): Disables Black's f-pawn push; holds material.
  3. `18. Ra1??` (-552 cp): Completely fatal. Allows `18...Qd5! 19. g3 fxe4 20. Nxe4 Re8` with unstoppable mating net.
- **Policy Distribution**:
  - #1 `Nxh7`: 58.58% (Unsound knight sacrifice)
  - #2 `Ng3`: 9.52%
  - #3 `Nf6+`: 8.79%
  - #41 `Qb3+`: 0.02% — Effectively pruned from root move consideration!
- **Counterfactual Verdict**:
  - `MW-0.2`: Plays `18. g4` (Score: -45 cp)
  - `R25-NOPOLICY`: Plays `18. g4` (Score: -45 cp)
  - `MW-R25-POLICY`: Plays `18. Ra1` (Score: -552 cp)
  - **Verdict**: Direct causal regression.

---

### Record 3: Move 20 — Walking Into Forced Mate (`20. Nxe4??` vs `20. Ne6`)

```yaml
id: R25_NEOMATICA_03
game: Round 25 vs neomatica
ply: 39
move_number: 20
fen: "5rk1/p5bp/b5p1/3q2N1/P3p3/2PnK1P1/3B1P1P/R2Q3R w - - 0 26"
model_version: MW-R25-POLICY (0d3741f)
played_move: g5e4 (Nxe4??)
best_move: d1b3 (Qb3) / g5e6 (Ne6!)
cpl: 500
eval_before_cp: -1066
eval_after_cp: -30000 (Mate in 8)
wdl_delta: Immediate forced loss
classification: TACTICAL
root_cause: >
  White is under heavy pressure after Ra1. 20. Nxe4?? grabs a pawn but removes the knight
  guarding the e-file, enabling 20...Re8! and forced mate in 8.
  MW-0.2 and R25-NOPOLICY found 20. Ne6!, interposing on the e-file and delaying mate.
regression_expectation: >
  Engine must avoid 20. Nxe4 and play 20. Ne6 or 20. Qb3.
training_status: RATED_HOLDOUT
```

---

## Comparison Matrix: MW-0.2 vs R25-NOPOLICY vs MW-R25-POLICY

| Move | Ply | FEN Summary | Played (POLICY) | Isolated MW-0.2 | R25-NOPOLICY | Stockfish 18 Best | Causal Attribution |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **14** | 27 | White +286 cp after pawn push | `Bd2` (+179 cp) | **`Rc1` (+286 cp)** | **`Rc1` (+286 cp)** | `Rc1` (+286 cp) | **Policy Regression** |
| **15** | 29 | Black queen pressure | `Rb1` (-107 cp) | `Rb1` (-107 cp) | `Rb1` (-107 cp) | `Qb1` (+185 cp) | Time / Horizon |
| **18** | 35 | King on e3, Black plays f5 | `Ra1??` (-552 cp) | **`g4` (-38 cp)** | **`g4` (-38 cp)** | `Qb3+` (+25 cp) | **Policy Regression** |
| **20** | 39 | Central e-file attack | `Nxe4??` (M-8) | **`Ne6` (-650 cp)** | **`Ne6` (-650 cp)** | `Qb3` (-600 cp) | **Policy Regression** |

---

## Action Plan for M17.5 Remediation

1. **Policy Soft-Gating & Tactical Override (Rule 12 & 27)**:
   Never allow raw policy scores to prioritize quiet moves over:
   - Forcing tactical candidate checks / queen trades (`Qb3+`)
   - Critical piece-pins and open-file controls (`Rc1`)
   - Immediate King-safety threats when in check or King exposed.

2. **Negative Mining on Delusional Sacrifice Patterns**:
   Add hard-negative distillation targets explicitly penalizing `Nxh7` when the Greek Gift sacrifice has zero tactical justification.

3. **Time-Management Horizon Adjustment**:
   Increase expected moves from 25 to 40 to prevent early clock starvation (clock was down to 28.5s by move 15).
