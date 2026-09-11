# Offline Stockfish benchmarks

Stockfish is an offline opponent and evaluator. The default submission package includes
only root Python modules and weights; it excludes baselines, tools, training data, and
the Stockfish executable. Never add the baseline with the packager's --include option.

The competition rules fetched on 2026-09-06 prohibit third-party engines and wrappers
in submissions, and permit engine-labelled training data:
https://aichessathon.com/docs/rules.md
https://aichessathon.com/docs/agent-contract.md

## Configuration

Set STOCKFISH_PATH to the executable, or use automatic PATH/WinGet discovery.
STOCKFISH_SKILL_LEVEL accepts 0–20 (default 5). STOCKFISH_TIME_PER_MOVE_MS optionally
sets a move budget, bounded by the remaining clock. STOCKFISH_THREADS defaults to 1.
A missing executable, invalid configuration, or failed query causes an error rather
than a random-move fallback. The UCI process persists within a game.

Skill levels 3, 5, and 8 are useful sparring settings; they are not verified Elo ratings.
Stockfish identity and executable hash are recorded in benchmark evidence.

## Position ACPL

```powershell
.venv/Scripts/python.exe tools/measure_acpl.py --positions 100 --target 40
```

The fixed development bank contains 25 positions in each of four categories: opening,
tactical, middlegame, and endgame. It retains the existing curated FENs; descriptive
labels are not a verified source-game provenance record or a certified tactic label.
It is an exposed development test, not an untouched holdout or a prediction of rated ACPL.

Each independent position uses a fresh process through the official runner. Import time
is separate from the move clock. The default agent input is time_left_ms=5000, not a
five-second fixed search: the agent's own time manager allocates the move budget.
Invalid moves, overruns, invalid positions, and oracle errors fail the run.

The oracle runs at full strength with one thread and 32 MB hash, independently of the
sparring level. Each comparison uses independent unrestricted and forced-root searches
of the same board, 0.1 seconds per search by default. Both scores use the mover's point
of view and are individually clipped to [-1000,1000] before max(0,best-played).
This project convention permits up to 2000 CPL on one move; it does not cap loss at 1000.
It is not asserted to reproduce a particular commercial site's ACPL implementation.
Use --eval-time to investigate oracle stability, keeping comparisons at the same setting.

Buckets are disjoint: best=0, good=(0,50], inaccuracy=(50,100], mistake=(100,200],
blunder>200. A failed target returns exit status 1. The report includes per-position
scores, FENs, timings, bank hash, agent hashes, and oracle identity.

Verified fresh-process run on 2026-09-06: 38.04 ACPL, passing the 40 target.
Opening 22.48; tactical 41.52; middlegame 37.08; endgame 51.08.
See experiments/r34/stockfish_benchmark/verified_acpl.json for exact evidence.
The old acpl_report.json predates corrected state isolation and scoring checks.

## Paired tournaments

```powershell
.venv/Scripts/python.exe tools/benchmark_stockfish.py --level 5 --pairs 10 --workers 1 --out experiments/r34/stockfish_benchmark/final_tournament
.venv/Scripts/python.exe tools/benchmark_stockfish.py --levels 3,5,8 --pairs 10 --out experiments/r34/stockfish_benchmark/tiers
.venv/Scripts/python.exe tools/candidate_screen.py --agent . --opponent baselines/stockfish --stockfish-level 5 --pairs 10 --out experiments/r34/stockfish_benchmark/screen
```

Each opening is played with both colours. Defaults are 5000+100 ms for the Stockfish
benchmark. One worker avoids competition among concurrent games on the local machine.
These settings and hardware are not the rated platform's 120000+500 ms environment.

Pair records and their PGNs are persisted together. Aggregated PGNs and reports are
rebuilt from these records on resume. A changed manifest requires a fresh directory.
ACPL is post-processed from all saved games, including resumed pairs, using a separate
full-strength oracle; per-agent-move losses are saved in acpl.json. It is not live
in-match oracle evaluation.

Final level-5 run: 20 games, 6 wins / 4 draws / 10 losses (40% score), with no
failed terminations. Full-game agent ACPL was 34.4996 across 1,143 moves, using
0.05-second oracle searches per comparison. Results and PGNs are under
experiments/r34/stockfish_benchmark/final_tournament/level_5/.

## Master-game datasets

```powershell
.venv/Scripts/python.exe training/scripts/build_extended_dataset.py --target-positions 32000 --shard-size 8000 --output-dir training/datasets/master_balanced_32k
```

Use a fresh output directory. The verified 32,000-position build contains 8,000 positions
from each of Carlsen, Kasparov, Karpov, and Fischer. Each shard has NPZ training tensors
and a JSONL provenance sidecar. Games must parse cleanly, use standard chess, and have
a decisive result; sampled moves come from the winning side. This is a quality
heuristic, not an engine-certified accuracy filter.

Full move-sequence hashes define game identities and deterministic train/val/test
assignment. Canonical positions are deduplicated across all splits. ACPL, screen,
confirm, and development bank positions are excluded; games containing later bank
positions are excluded as well. No synthetic self-play or benchmark examples fill
a source shortfall.

The larger requested 100,000-position attempt yielded 78,524 positions and reports
complete=false, because Kasparov and Fischer exhausted their filtered input before
the per-source quota. It remains available in master_extended_verified_100k.
An integrity audit found zero duplicate positions, cross-split game overlap, or
benchmark-position overlap in those 78,524 records.
The same audit passed for all 32,000 balanced records: train 27,242, validation
3,356, and test 1,402.

The NPZ shards work with the existing teacher pipeline:

```powershell
.venv/Scripts/python.exe training/scripts/train_teacher.py --dataset-dir training/datasets/master_balanced_32k --checkpoint-dir training/checkpoints/master_balanced_teacher
```

Training and exporting a new policy remain conditional on measured benefit. No new
weights were trained or promoted for this integration; the corrected development
ACPL already met the target. Any future candidate still needs paired strength and
reliability gates before replacing the current policy.

## Verification

All 80 regression tests passed, as did Ruff and strict mypy across 93 files.
The standalone packaging determinism test passed. The built agent.zip is
4,881,625 bytes compressed and 5,354,451 bytes uncompressed; ZIP integrity and
exclusion of offline files were checked. No engine-strength changes, new weights,
or competition upload were made during this integration.
