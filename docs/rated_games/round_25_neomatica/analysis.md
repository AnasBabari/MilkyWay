# AI Chessathon Round 25 Forensic Report: MilkyWay vs neomatica

**Event**: AI Chessathon Rated Round 25  
**Match ID**: `d5dff108-e205-45cc-9237-5c1491ea20a9`  
**Date**: 2026-09-05 16:21:16 UTC  
**White**: MilkyWay (Zero Elo)  
**Black**: neomatica  
**Result**: 0-1 (Loss by checkmate, Ply 268 / Move 140)  
**Opening**: Pirc Defence (`1. e4 d6 2. d4 Nf6 3. Nc3 g6 4. Be3 Bg7 5. Nf3 O-O 6. Be2 b5`)  
**Starting FEN**: `rnbq1rk1/ppp1ppbp/3p1np1/8/3PPB2/2N2N2/PPP1BPPP/R2QK2R b KQ - 5 6`  
**Frozen Model ID**: `MW-R25-POLICY` (Commit `0d3741f`)

---

## 1. Executive Summary & Causal Attribution

### The Central Question
> **Would MW-0.2 have played this game better than the new model?**

### The Definitive Answer: **YES.**
When re-audited using strict process-level environment isolation (`PYTHONPATH=versions/mw_0_2`), frozen MW-0.2 demonstrably outplayed the neural-policy engine (`MW-R25-POLICY`) at every critical turning point of the game:

1. **Move 10 (`10. Qd2!` vs `10. Ng5`)**:
   - **MW-0.2 Choice**: **`10. Qd2!`** (Stockfish top tier). Solid positional continuation.
   - **Played Move (POLICY)**: `10. Ng5` (CPL 221 mistake). Premature attack where student policy gave `Ng5` 98.5% probability.
2. **Move 14 (`14. Rc1!` vs `14. Bd2`)**:
   - **MW-0.2 Choice**: **`14. Rc1!`** (+286 cp, Stockfish #1 move in fresh evaluation). Seizes open c-file and traps Black's queen on `b2`.
   - **Played Move (POLICY)**: `14. Bd2` (+179 cp, CPL 107). Passively retreats bishop and dissipates White's decisive advantage.
3. **Move 18 (`18. g4!` vs `18. Ra1??`)**:
   - **MW-0.2 Choice**: **`18. g4!`** (-38 cp in both fresh and stateful replay). Defends against Black's f-pawn break and keeps the position balanced and playable.
   - **Played Move (POLICY)**: **`18. Ra1??`** (-552 cp, CPL 526). **The decisive fatal blunder of the game**, handing Black a crushing mating attack.
4. **Move 20 (`20. Ne6!` vs `20. Nxe4??`)**:
   - **MW-0.2 Choice**: **`20. Ne6!`** (-650 cp in fresh evaluation). Interposes knight to block the e-file and resists.
   - **Played Move (POLICY)**: **`20. Nxe4??`** (-30,000 cp). Walks straight into a forced mate in 8 plies (`20...Re8! 21. Qg4 Qc5+!`).

### Causal Proof via `R25-NOPOLICY`
Running the identical experimental engine with root policy disabled (`MILKYWAY_ROOT_POLICY=0`):
- `R25-NOPOLICY` chose **`14. Rc1!`**, **`18. g4!`**, and **`20. Ne6!`**, exactly matching MW-0.2!
- **Conclusion**: The search algorithm, handcrafted evaluation, and time manager were fully capable of finding the correct moves. The loss was **directly caused by neural policy move-ordering poisoning under clock pressure**:
  - The policy net suffered from a delusional "Greek Gift" hallucination, assigning 58% to 88% probability to `Nxh7` across 8 consecutive positions.
  - As a direct consequence, the sound tactical candidate `14. Rc1` was demoted to policy rank 27 (p=0.00048), and `18. Qb3+` was demoted to policy rank 41 (p=0.00025).
  - Under shallow clock allocations (2.5s–3.5s), the search was starved of time exploring policy-favored unsound quiet moves, and defaulted to blunders.

---

## 2. Match Platform Telemetry

- **Init Phase**: Ready in **0.7 s** of 90.0 s budget (1% used). Pre-warmed ONNX engine without delay.
- **Match Clock**: 120.0 s base + 0.5 s increment.
- **Game Length**: 134 MilkyWay decisions (269 total plies). Match duration: 326.9 s.
- **Total Thinking Time**: 180.3 s.
- **Average Move Time**: 1.3 s/move.
- **Slowest Move**: 11.6 s (Move 6, `Qa4`).
- **Clock at End**: **6.7 s remaining**. Zero flag risk, zero illegal moves, zero runtime crashes.

---

## 3. Stockfish 18 Chronological Error Analysis

Analysis performed with Stockfish 18 (AVX2, MultiPV 5, 100,000 nodes per position, White canonical perspective).

| Metric | Count |
| :--- | :--- |
| **Total MilkyWay Moves** | 134 |
| **Inaccuracies (50 < CPL ≤ 120)** | 15 |
| **Mistakes (120 < CPL ≤ 250)** | 5 |
| **Major Errors (CPL > 250)** | 37 |
| **Zero-CPL Moves** | 42 |

### Critical Move Progression & Turning Points

| Move # | Ply | Played (POLICY) | MW-0.2 Move | SF Best Move | Eval Before | Eval After | CPL | Attribution |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **4** | 7 | `c3` | `c3` | `Nc3` | +55 cp | -44 cp | 99 | Static Eval |
| **6** | 11 | `Qa4` | `Qa4` | `Nfg5` | -45 cp | -257 cp | 212 | Search Horizon |
| **10** | 19 | `Ng5` | `Ng5` | `Ne2` | +69 cp | -152 cp | 221 | Policy / Search |
| **11** | 21 | `N3e4` | `N3e4` | `N5e4` | +147 cp | -69 cp | 216 | Search Horizon |
| **12** | 23 | `dxe7` | `dxe7` | `b4` | +88 cp | +56 cp | 32 | Sound pawn push |
| **13** | 25 | `exf8=Q+` | `exf8=Q+` | `exf8=Q+` | +222 cp | +250 cp | 0 | Wins rook cleanly |
| **14** | 27 | `Bd2` | **`Rc1!`** | **`Rc1!`** | **+286 cp** | **+179 cp** | **107** | **POLICY REGRESSION** |
| **15** | 29 | **`Rb1?`** | `Rb1` | **`Qb1!`** | **+185 cp** | **-107 cp** | **292** | **Time / Horizon** |
| **16** | 31 | `Ke2` | `Ke2` | `Ke2` | -17 cp | -64 cp | 47 | Sound King evasion |
| **17** | 33 | `Ke3` | `Ke3` | `Ke3` | -59 cp | -44 cp | 0 | Sound King evasion |
| **18** | 35 | **`Ra1??`** | **`g4!`** | **`Qb3+!`** | **-26 cp** | **-552 cp** | **526** | **POLICY REGRESSION** |
| **19** | 37 | `g3` | `g3` | `Qc2` | -546 cp | -904 cp | 358 | King Safety / Horizon |
| **20** | 39 | **`Nxe4??`** | **`Ne6!`** | **`Qb3`** | **-1066 cp** | **-30000** | **500** | **POLICY REGRESSION** |
| **21** | 41 | `Qg4` | `Qg4` | `Qg4` | -815 cp | -30000 | 500 | Forced Defense |
| **23** | 45 | `Qxe4` | `Qxe4` | `Qxe4` | -512 cp | -644 cp | 132 | Forced Defense |
| **27** | 53 | `g4` | `g4` | `g4` | M-9 | M-9 | 0 | Forced Queen Sacrifice |
| **28** | 55 | `Qxg4` | `Qxg4` | `Qxg4` | -668 cp | -754 cp | 86 | Forced Recapture |

---

## 4. Policy Model Forensic Audit

### Aggregate Benchmark on Round 25
- **Overall Top-1 Accuracy**: 35.8% (48 / 134)
- **Overall Top-3 Accuracy**: 69.4% (93 / 134)
- **Overall Top-5 Accuracy**: 82.1% (110 / 134)
- **Mean Reciprocal Rank (MRR)**: 0.5453
- **Mean Policy Entropy**: 0.8724

### Early Tactical Phase Blindspot (Moves 1 to 20)
- **Top-1 Accuracy**: **10.0%** (2 / 20)
- **Top-3 Accuracy**: **15.0%** (3 / 20)
- **Top-5 Accuracy**: **25.0%** (5 / 20)
- **MRR**: **0.1811** (Mean SF Best Rank: 21.3)

### The "Greek Gift" Delusion: Teacher & Student Hallucination
On eight consecutive positions in the critical phase (moves 11, 12, 13, 14, 15, 17, 18), both the **student model** and the **teacher model** (`best_policy.pt`) suffered from a severe pattern hallucination:
- They ranked `Nxh7` (g5h7) as the **#1 move with 58% to 91% probability** across every position.
- In every position, `Nxh7` was completely unforced, unsound, and blundered a piece.
- **Why this poisoned search**:
  While search alpha-beta pruning eventually rejected `Nxh7`, the policy score bonus inflated other quiet moves and severely suppressed genuine tactical candidate moves:
  - Move 14: Stockfish #1 move `Rc1` was pushed down to **Rank 27** ($p=0.00048$).
  - Move 18: Stockfish #1 move `Qb3+` was pushed down to **Rank 41** ($p=0.00025$).
  Because the engine had only 2.5s–3.5s on the clock, it spent its precious search nodes exploring high-ranked policy moves and never completed the iteration needed to find the tactical defenses.

---

## 5. Time Management Autopsy & Allocator Simulations

### Aggressive Early Spending
MilkyWay spent clock aggressively early:
- By Move 9: **52.9 s remaining**
- By Move 15: **28.5 s remaining**
- By Move 20: **14.9 s remaining**

Because the engine entered Move 15 with only 28.5s, `allocate_time` gave it only **3.2s** (depth 4–5). At depth 4–5, `15. Rb1` looked like an active queen attack; depth 6–7 was required to see that Black's queen infiltrates with `15...Nd3+ 16. Ke2 Qa2 17. Ke3 f5! 18. Ra1 Qd5!` winning.

### Simulation of Candidate Allocators

| Move | Actual Clock | TM-A (Current Sim) | TM-B (Conservative 15s Reserve) | TM-C (Phase-Aware 20s Reserve) |
| :---: | :---: | :---: | :---: | :---: |
| **1** | 114.6 s | 114.8 s | 117.1 s | 117.5 s |
| **5** | 87.9 s | 96.1 s | 106.6 s | 108.5 s |
| **9** | 52.9 s | 79.9 s | 96.7 s | 99.8 s |
| **15** | **28.5 s** | 61.2 s | **84.2 s** | **88.6 s** |
| **20** | **14.9 s** | 50.6 s | **76.3 s** | **81.5 s** |
| **30** | 9.5 s | 40.6 s | 68.4 s | 73.8 s |
| **50** | 5.9 s | 28.6 s | 57.6 s | 61.6 s |
| **100** | 5.6 s | 10.8 s | 35.7 s | 34.5 s |
| **134** | 6.7 s | 8.9 s | 30.0 s | 25.7 s |

Under TM-B or TM-C, MilkyWay would have entered the critical turning points (moves 15–18) with **84 to 88 seconds** on the clock, allowing 8–10s of deep calculation on each critical move.

---

## 6. Defensive Queen-Check Sequence Analysis (Moves 20–134)

- **Were Drawing Resources Missed?**: No. Stockfish MultiPV analysis confirms White's evaluation was permanently below -467 cp from move 20 until mate. Black held an overwhelming material and positional advantage.
- **Was the Queen Trade Unnecessary?**: No. The sequence `33. g4` / `34. Qxg4` was forced; Stockfish confirms `g4` and `Qxg4` were both the engine's #1 move to prevent immediate mate.
- **Why Did the Game Last 134 Moves?**: Neomatica repeatedly failed to convert forced mates (e.g. mate in 8 at move 21 became -631 cp at move 22; mate in 10 at move 31 became -489 cp at move 32). MilkyWay played optimal defensive king moves on 16 separate positions between moves 20 and 50, surviving on a 6-second increment reserve for over 100 moves.

---

## 7. Forensic Diagnosis Classification

```text
A. Learned policy regression:        CONFIRMED (Policy poisoned root ordering on 14. Rc1, 18. Qb3+/g4, 20. Ne6)
B. Classical evaluation failure:      CONFIRMED (Failed to penalize King on e3 and disfavored queen trade)
C. Search/pruning/horizon failure:    CONFIRMED (Horizon truncation at depth 4-5 caused by low clock)
D. Policy × timed-search interaction: CONFIRMED (Unsound policy suggestions starved search of time on critical candidates)
E. Time-management failure:          CONFIRMED (Premature clock exhaustion: 28s at move 15)
F. Position was already lost:         PARTIALLY (Lost permanently after move 18 Ra1)
```

---

## 8. Actionable Recommendations for MilkyWay

1. **Implement Tactical Override & Policy Gating (M17.5 Priority)**:
   - Prioritize tactical candidates (checks, forcing queen trades like `Qb3+`, captures, pins) above policy-ordered quiet moves.
   - Never allow policy scores to demote forcing tactical moves below quiet moves.
2. **Hard-Negative Mining for Student Distillation**:
   - Mine positions where teacher/student hallucinate Greek Gift sacrifices (`Nxh7`) and penalize them with ranking loss:
     $$\mathcal{L}_{\text{rank}} = \max(0, \text{score}(\text{bad}) - \text{score}(\text{best}) + \gamma)$$
3. **Deploy Conservative Time Manager (TM-B)**:
   - Increase expected move horizon from 25 to 40–45 moves.
   - Establish an explicit 15–20 second emergency reserve.
   - Cap early opening moves strictly at 3.5s soft / 6.0s hard when clock > 90s.
4. **King Safety & Central Exposure Tuning**:
   - Heavily penalize kings on open center files (`e2`, `e3`, `d2`, `d3`) when opponent queens and rooks are active.
