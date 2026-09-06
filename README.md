# MilkyWay ♜

A from-scratch chess engine built for the 2026 AI Chessathon.

**Current competition build: MW-0.2 — platform validated**

## Competition status

**MilkyWay MW-0.2** — validated for AI Chessathon on 5 September 2026.

- Platform validation: passed
- Init time: 0.5–0.7 s
- Validation smoke games: passed as White and Black
- Submission size: 71,835 bytes uncompressed
- Search: iterative deepening PVS/alpha-beta with TT, quiescence,
  aspiration windows, LMR, null-move pruning and futility pruning
- Evaluation: tapered handcrafted evaluation
- Runtime: Python 3.12 / single CPU core

## Architecture

MilkyWay is a classical competition engine adhering to all platform constraints (1 CPU core, 2 GB RAM, 120s + 0.5s TC, 90s init budget, max 50 MB uncompressed zip at root, no network/GPU, no native binaries, readable Python source).

```text
agent.py            competition entrypoint (get_move)
constants.py        scores, PSTs, tunable eval coefficients (EvalParameters)
engine.py           persistent game state, fallback move, repetition avoidance
engine_types.py     TTEntry, SearchStats, SearchTimeout
evaluation.py       tapered handcrafted eval (centipawns, bitboard-optimized)
move_ordering.py    TT move, promotions, MVV-LVA captures, killers, history
search.py           iterative deepening + PVS alpha-beta + quiescence + pruning
time_manager.py     soft/hard deadlines + emergency mode (time.monotonic)
transposition.py    bounded TT with generations (EXACT/LOWER/UPPER)
```

## Search & Evaluation Details

- **Search**: Negamax with mate-distance scores (`MATE - ply`), TT cutoffs with mate adjustments, null-move pruning, late move reductions (LMR) with re-search, futility and reverse futility pruning, check extensions, aspiration windows, quiescence search with delta pruning and evasions.
- **Evaluation**: Tapered evaluation interpolating between middlegame and endgame phases across material, piece-square tables, pawn structure (doubled, isolated, backward, passed by rank, protected), rook activity (open files, 7th rank), mobility, king safety, and mop-up endgame positioning.
- **Time Management**: Proportional safety margin with soft and hard deadlines, 64-node emergency polling, and instant legal fallback to prevent flag losses.
- **Transposition Table**: Bounded memory footprint with $O(1)$ FIFO replacement policy and cross-move persistence.

## Development & Verification

```bash
# Setup dependencies
make setup

# Run test suites (39 unit tests)
uv run python -m unittest discover -s tests

# Quality gates
make gate

# Benchmarking & parity
uv run python tools/diff_eval.py --positions 1000
uv run python tools/time_probe.py
uv run python tools/paired_arena.py --opponent versions/mw_0_2 --bank neutral

# Build competition zip
uv run python -m harness.package --out agent.zip
```

Milestones, benchmarking logs, and tuning experiments are documented in `IMPLEMENTATION_PLAN.md` and `BENCHMARKS.md`.

## Upstream sync notes (2026-09-06)

Synced with `advitrocks9/aichessathon-starter`: the harness now suspends
agents while the opponent thinks, annotates PGNs with clocks and names,
draws only on the actual third repetition / fifty moves / 600-ply cap, and
local games start from eight curated openings. `make zip` now auto-includes
imported local packages and plays two full-clock smoke games from the built
zip, so packaging failures surface locally instead of on the platform.
