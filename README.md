# MilkyWay

A Python chess engine developed for the 2026 AI Chessathon, combining classical
alpha-beta search, handcrafted evaluation and experiments with learned evaluation
and root policy.

**Final event record: 102 rated games · 47 wins · 12 draws · 43 losses**

**Peak event Elo: 1556** — final dashboard figures supplied by the project owner.

## What it does

Given a chess position and the time remaining, MilkyWay explores possible replies,
scores the resulting positions and returns a legal move before its clock expires.
It reuses earlier search results and spends less time on unlikely alternatives.

The root source preserves the Python engine with ONNX root policy enabled by
default when the model loads. The last documented packaged build uses a separate
original Numba search engine and compact learned value model. The exact final
successful platform upload is not established by the repository. See
[build provenance](docs/BUILD_PROVENANCE.md) for the distinction and checksums.

## Architecture

| Module | Purpose |
| --- | --- |
| `agent.py` | FEN input, UCI output and final legality check |
| `engine.py` | Persistent game state, fallback move and search orchestration |
| `search.py` | Iterative deepening, PVS/alpha-beta, quiescence and pruning |
| `evaluation.py` | Tapered handcrafted scoring of material, placement and structure |
| `move_ordering.py` | Prioritize promising moves so pruning works earlier |
| `transposition.py` | Cache positions reached through different move sequences |
| `time_manager.py` | Allocate time, preserve reserves and handle emergencies |
| `root_policy.py` | Optional single-core ONNX scores for root move ordering |

**Iterative deepening** keeps the last completed answer while attempting a deeper
search. **PVS/alpha-beta** skips branches that cannot improve that answer.
**Quiescence** follows tactical exchanges beyond the nominal depth. **Late move
reductions**, **null-move pruning** and **futility pruning** trade some completeness
for greater useful depth. **Tapered evaluation** blends middlegame and endgame
priorities. [Architecture details and move pipeline](docs/ARCHITECTURE.md).

## Performance work

Historical local profiling of MW-0.1 to MW-0.2 documented:

| Measurement | Before | After | Change |
| --- | ---: | ---: | ---: |
| Evaluation calls/second | 5,225 | 14,774 | 2.83x |
| Fixed-depth search nodes/second | 5,034 | 10,519 | 2.09x |

Bitboard operations, fewer temporary objects, leaner ordering and bounded cache
eviction reduced overhead. Changes were differential-tested and game-tested.
These are historical host measurements, not a fresh benchmark or a direct Elo
claim. [Benchmarks, methods and harness caveats](docs/BENCHMARKS.md).

## Engineering methodology

**PROFILE → HYPOTHESIS → CHANGE → MEASURE → ARENA → KEEP / REVERT**

Frozen opponents, paired matches, confidence intervals, held-out banks,
legal-position fuzzing, clock probes and rated-game regression positions provided
different kinds of evidence. Faster code or lower training loss did not guarantee
promotion. [Selected experiments and rejected candidates](docs/EXPERIMENTS.md).

## Neural experiment

Team-trained models were developed offline using GPUs and exported to ONNX for
single-core CPU inference. The Python policy influences root ordering rather than
replacing the handcrafted leaf evaluator. Its 40-game ON/OFF ablation scored 50%;
the broader RC1 candidate failed its full-clock promotion gate. The later compiled
build used a separate compact learned residual. Neither experiment justifies
crediting the network with all engine strength or the event record.

## Reliability

The project targets Python 3.12 and a single-core competition runtime with strict
wall-clock limits. Legal-move fallback, time-budget probes, fuzz/regression tests
and extracted-package smoke games complement CI. The workflow runs the Linux
gate and Windows/macOS harness jobs. See the [verification report](docs/cleanup/REPORT.md)
for the actual cleanup checks and any limitations.

## Running locally

Install [uv](https://docs.astral.sh/uv/), then run from the repository root:

```bash
uv sync
uv run ruff check .
uv run mypy
uv run python -m unittest discover tests
make play
make arena
make gate
make zip
```

On Windows without Make, use `uv run python -m harness.play --white . --black
baselines/greedy` to play, `uv run python -m harness.arena --opponent
baselines/greedy` for an arena, and `uv run python -m harness.package` to package
and smoke-test the extracted build. The Makefile shows the exact gate commands.
Building from the root packages the root Python engine, not the historical TM ZIP.

## Repository structure

```text
agent.py + engine modules   maintained Python implementation
baselines/  harness/        local opponents and competition protocol
docs/                      architecture, benchmarks and postmortem
experiments/               selected historical result records
tests/  tools/             regression tests and measurement utilities
training/                  offline data, training and export source
versions/                  frozen milestones and exact last packaged source
weights/                   root runtime ONNX model
artifacts/final/           last documented competition ZIP and checksum
```

## Competition

[AI Chessathon](https://aichessathon.com/) challenged participants to build chess
agents under constrained runtime and packaging conditions. The event is complete.
Read the [engineering postmortem](docs/POSTMORTEM.md) for the development journey,
final result and lessons. The full research workspace remains available at the
[archive tag](https://github.com/AnasBabari/MilkyWay/tree/aichessathon-2026-final-workspace).

## Acknowledgements

This repository began as a fork of the
[official AI Chessathon starter](https://github.com/advitrocks9/aichessathon-starter),
which provided the local harness and baselines. The MilkyWay chess engine, search,
evaluation, time management, experiments and learned-policy work were developed
for the competition. License: [MIT](LICENSE).
