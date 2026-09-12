# AI Chessathon Round 20 Diagnostic: MilkyWay vs LARPMAXX

**Event**: AI Chessathon Rated Round 20  
**Match ID**: `d9767340-99c9-409b-9471-acb8f6289003`  
**Date**: 2026-09-05 11:15:16 UTC  
**White**: MilkyWay (Zero Elo)  
**Black**: LARPMAXX  
**Result**: 0-1 (Checkmate on move 24)  
**Opening**: Sicilian Closed (`1rbqk1nr/pp2ppbp/2np2p1/2p5/P3P3/2NP2P1/1PP1NPBP/R1BQK2R b KQk - 0 7`)

---

## 1. Executive Summary & Clock Review

- **Init Budget**: Ready in **0.5 s** of 90.0 s (1% of budget used).
- **Match Clock**: 120 s + 0.5 s increment.
- **Time Management**: Total time used across 17 decisions: **100.1 s**; average **5.9 s/move**; slowest **10.3 s** (move 7).
- **Clock at Game End**: **28.4 s remaining**. Clock management was completely sound; zero flag or time trouble risk.
- **Root Failure**: Move 19 (`19. g4??`) voluntarily leaving bishop on c8 en prise.

---

## 2. Critical Position 1: Move 19 (`g3g4??`)

```text
FEN: 1rBq1r2/1p3p1k/2n3pb/p1p4p/P3Pp1P/3P2P1/1PPQ1P2/R2R2K1 w - - 0 19
```

### Context
Preceding moves:
```text
17. Bh3 e5
18. Bxc8 exf4
```
Black's pawn on f4 set up a discovered attack by the bishop on h6 against White's queen on d2 if the f-pawn moves. White's bishop on c8 was also attacked by Black's queen on d8.

MilkyWay played:
```text
19. g4??
```
Black responded `19...Qxc8` winning the bishop cleanly, followed by `20. gxh5 Qg4+ 21. Kh2 f3!` and mate on move 24.

---

## 3. Reproduction & Depth Breakdown

Running MW-0.2 on `1rBq1r2/1p3p1k/2n3pb/p1p4p/P3Pp1P/3P2P1/1PPQ1P2/R2R2K1 w - - 0 19`:

### Reproduction Status: **CONFIRMED**
At 46,948 ms clock budget (matching the game clock), MW-0.2 chooses `g3g4` after ~4.4 s of search.

### Depth-by-Depth Root Move Progression

| Depth | Best Move | Score | Rank of `g3g4` | Score of `g3g4` | Best Move PV |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Depth 1** | `c8h3` (Bh3) | -345 cp | 22 / 35 | -640 cp | `Bh3` |
| **Depth 2** | `c8h3` (Bh3) | -345 cp | 22 / 35 | -640 cp | `Bh3` |
| **Depth 3** | `c8b7` (Bxb7) | -497 cp | 7 / 35 | -625 cp | `Bxb7` |
| **Depth 4** | `c8b7` (Bxb7) | -497 cp | 9 / 35 | -654 cp | `Bxb7` |
| **Depth 5** | `c8f5` (Bf5) | -621 cp | 4 / 35 | -654 cp | `Bf5` |
| **Depth 6** | **`g3g4` (g4)** | **-631 cp** | **1 / 35** | **-631 cp** | **`g3g4 d8c8`** |

### Root Move Scores at Depth 6 (Production Search)

```text
1. g3g4 (g4)    : -631 cp (PV: g3g4 d8c8)
2. d2c3 (Qc3)   : -645 cp (PV: d2c3 b8c8)
3. c8h3 (Bh3)   : -658 cp (PV: c8h3 f4g3)
4. c8f5 (Bf5)   : -662 cp (PV: c8f5 f4g3)
5. c8b7 (Bxb7)  : -670 cp (PV: c8b7 f4g3)
6. g3f4 (gxf4)  : -712 cp (PV: g3f4 d8c8)
7. c8e6 (Be6)   : -813 cp
8. c8g4 (Bg4)   : -815 cp
```

---

## 4. Search Ablation Matrix (Depth 6)

Tested using `tools/analyze_position.py --depth 6 --ablation-matrix`:

| Configuration | Best Move | Score | Nodes | QNodes |
| :--- | :--- | :--- | :--- | :--- |
| **1. Production (Full MW-0.2)** | `g3g4` | **-631** | 31,157 | 30,515 |
| **2. No TT** | `g3g4` | **-631** | 33,095 | 32,913 |
| **3. No LMR** | `g3g4` | **-631** | 52,321 | 39,880 |
| **4. No Null Move** | `g3g4` | **-631** | 33,371 | 32,615 |
| **5. No Futility** | `g3g4` | **-631** | 46,530 | 44,063 |
| **6. No Reverse Futility** | `g3g4` | **-631** | 38,082 | 43,160 |
| **7. No Aspiration** | `g3g4` | **-631** | 31,157 | 30,515 |
| **8. Conservative Alpha-Beta (No Pruning)** | **`d2c3`** | **-645** | 355,553 | 321,494 |
| **9. Pure Minimax (No TT, No Pruning)** | **`d2c3`** | **-645** | 356,238 | 322,320 |

### Specific Ablations on `g3g4` Score:
- Production: `g3g4` score = **-631 cp**
- No LMR alone: `g3g4` score = **-631 cp**
- No Reverse Futility alone: `g3g4` score = **-631 cp**
- **No LMR + No Reverse Futility**: `g3g4` score = **-967 cp**!
- **Conservative (Unpruned) Search**: `g3g4` score = **-967 cp**!

---

## 5. Root Cause Analysis

The blunder `19. g4` was caused by a combination of two distinct search phenomena:

### Phenomenon A: LMR Pruned Black's Direct Refutation `19...Nd4!`
After `19. g4`, Black possesses the crushing tactical fork `19...Nd4!`:
- Threatens `Nf3+` winning the White queen and king.
- The bishop on c8 remains hanging to `Qxc8`.
- In unpruned search, `19...Nd4!` evaluates to **+967 cp** for Black (-967 cp for White).
- **Why LMR pruned it**:
  - `19...Nd4` is a quiet move (index 8 in move list, after 5 captures).
  - LMR reduced `19...Nd4` from depth 5 to depth 3/4.
  - At reduced depth 3/4, the search only sees `20. Kf1 ...Qxc8` (+620 cp for Black).
  - Because `19...Qxc8` had already set $\alpha = +631\text{ cp}$, `Nd4` failed low against the null window ($620 \le 631$).
  - `Nd4` was discarded without full-depth re-search, and Black's score under `19. g4` remained capped at `+631 cp` (`19...Qxc8`).

### Phenomenon B: Horizon Effect under `19...Qxc8 20. gxh5`
Even against `19...Qxc8`, `20. gxh5??` walks directly into a forced mate:
- `20...Qg4+ 21. Kh2 f3! 22. hxg6+ fxg6 23. Qxh6+ Kxh6 24. Nd5 Qg2#`.
- The quiet mating threat `21...f3!` occurs at ply 6, with mate delivered at ply 9.
- At Depth 6 from move 19, the search stops at ply 4 (`20...Qg4+ 21. Kh2`), where quiescence search stands pat at **-631 cp**.
- Because `f3` is a quiet move, quiescence search does not explore it.
- Only at Depth 7 does the search uncover the mate, dropping `20. gxh5` to **-903 cp**.
- Meanwhile, all alternatives (`19. Bh3`, `19. Bf5`, `19. Bxb7`) immediately faced `19...fxg3!` on ply 2 (discovered attack on Queen d2), evaluating to `-658` to `-670 cp`.
- Since `-631 > -658`, White falsely believed `19. g4` was the highest-scoring move.

---

## 6. Critical Position 2: Move 23 (`23. Qxh6+`)

```text
FEN: 1r3r2/1p5k/2np2pb/p1p5/P3P1qP/2NP1p2/1PPQ1P1K/R2R4 w - - 0 23
```

### Finding: **`23. Qxh6+` was NOT a blunder; it was forced mate delay.**
- Black's Queen on g4 and pawn on f3 threaten unstoppable checkmate via `23...Qg2#`.
- **All 26 other legal moves** allow immediate mate in 1: score = **-99,998 cp**.
- Only two moves delay mate:
  - `23. Qxh6+` (checks Black king, forcing `23...Kxh6`): score = **-99,996 cp** (delays mate by 1 ply).
  - `23. Qg5` (blocks g2, captured by `23...Bxg5`): score = **-99,996 cp**.
- White was already completely lost by move 23; `Qxh6+` was the engine correctly playing the longest surviving resistance.

---

## 7. Conclusions & Next Steps for MW-0.3

1. **MW-0.2 Stability Confirmed**: No crash, no illegal move, zero clock faults (28.4s left at game end).
2. **Search Diagnostics Needed**:
   - **Tactical LMR Guard**: Do not reduce quiet knight or bishop moves that jump into advanced outposts / enemy territory (e.g. `Nd4` attacking squares near the King) or when the piece moves into an attacking zone.
   - **Mating Threat Awareness**: Investigate extending search or qsearch checks when king zone is breached.
3. **Regression Tests**: Add `ROUND20_LARPMAXX_CRITICAL` and `ROUND20_LARPMAXX_MATE_DEFENSE` to `tests/test_rated_regressions.py`.
