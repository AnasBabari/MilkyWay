# engine-v2 candidate (staged 2026-09-06)

Consolidated here from `ultimatemoneymachine/artifacts/milkyway/engine-v2/`
so all engine work lives in this repo. Source directory removed after
hash-verified copy.

## What it is

A minimal candidate: repo root working tree with exactly ONE file changed
(`engine.py`). All other 9 runtime `.py` files are byte-identical to the
repo root working tree (which itself carries uncommitted `evaluation.py`
KS_C-default and `search.py` qsearch changes — see `git status`).

## The delta (`candidate/engine.py` vs root `engine.py`)

1. **Search-depth limit removed.** `max_depth = 4 if budget.emergency else 64`
   plus the `time_left_ms < 6000 → cap at 6/4` clamp is replaced with
   `max_depth = 4 if time_left_ms < 1200 else 64`. Rationale in the code
   comment: a fixed depth ceiling wastes allocated time in low-branching
   positions (e.g. pawn endings needing long lines); iterative deepening
   with soft/hard deadlines already bounds thinking time.
2. **Root-policy scores plumbed into search**: `get_root_evaluator()`
   move scores passed as `root_policy_scores` to `searcher.new_search()`
   (fails soft to `{}` when unavailable).

## Evidence carried over

- `acpl-candidate.json`: 100-position ACPL **38.14** vs target 40
  (Stockfish 18 oracle, 0.1 s/search, ±1000 cp cap). Category split:
  opening 23.04, tactical 41.6, middlegame 36.72, endgame 51.2.
- `validate_candidate.py`: runs the repo unit suite with imports forced to
  the candidate dir (`--repo … --candidate …`); aborts if any runtime
  module resolves elsewhere.

## Weights (NOT duplicated here)

`weights/milkyway_policy.onnx` in the source tree was byte-identical (sha256
match) to repo `weights/milkyway_policy.onnx` and was deliberately not
copied. To materialize a runnable candidate dir for harness play:

```powershell
New-Item -ItemType Directory -Path experiments/engine-v2/candidate/weights -Force | Out-Null
Copy-Item weights/milkyway_policy.onnx -Destination experiments/engine-v2/candidate/weights/
```

Remove the copied model after validation runs; do not commit binaries.

## Status / next steps

Staged, NOT validated as an upgrade and NOT promoted. Required before any
promotion claim: `validate_candidate.py` green, paired arena vs current
root (frozen `experiments/r34/checkpoint` semantics), reliability gates
(fuzz/time-probe/smoke both colours), then packaging checks. The prior
session's `baseline/` copy was working-tree state reconstructible from git
plus the documented delta, so it was not carried over.
