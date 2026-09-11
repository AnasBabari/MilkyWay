# Project Astralix — flagship engine v1

Codename **astralix** for the next enhanced MilkyWay competition engine:
classical search + a jointly trained policy/value network used once per
move at the root.

## v1 definition (frozen candidate directory)

Base: post-upstream-sync `main` (HEAD) runtime files, plus:

1. **Depth-limit removal** (`engine.py`): `max_depth = 4 if
   time_left_ms < 1200 else 64`. The old depth-6 clamp for sub-6 s clocks
   wasted allocated time in low-branching positions; iterative deepening
   with soft/hard deadlines already bounds thinking time.
2. **Joint policy+value network** (`weights/milkyway_astralix.onnx`, 5.5 MB,
   0.5 ms joint inference on one CPU core): 18x8x8 input, 64ch x4 ResBlock
   trunk warm-started from the shipped policy student, policy head retained
   (top-1 0.22 vs 0.15 shipped on held-out masters), value head trained on
   Stockfish WDL labels over 72,002 GM positions from 12 players
   (55,384 games analyzed) plus 5 rated games. See
   `training/checkpoints/flagship_v2/` and `training/datasets/master_value_v2/`.
3. **Sensor fusion** (`engine.py`): learned value blended with exact static
   eval by material imbalance (net trusted near level, counting trusted at
   extremes where training mass is thin).
4. **Uncertainty time scaling** (`engine.py`): |value − last search score|
   scales the soft deadline within [0.9x, 1.35x], never past hard.

Deliberately NOT included: uncommitted working-tree KS_C/qsearch
experiments (separate attribution track), v3/v4 checkpoints (diverged or
suspect dual-writer provenance — see training log notes).

## Running

Weights ship inside this directory (excluded from git; re-materialize with
the export script if missing). Point any agent-dir runner at
`experiments/astralix/v1`:

```powershell
.venv/Scripts/python.exe tools/benchmark_stockfish.py --agent experiments/astralix/v1 --level 6 --pairs 6 --base-ms 30000 --increment-ms 300 --workers 1 --out experiments/astralix/sf6_baseline
```

Set `MILKYWAY_ROOT_POLICY=0` in the environment for the classical-only
(depth-delta) ablation: policy scores go empty and the value path idles.
