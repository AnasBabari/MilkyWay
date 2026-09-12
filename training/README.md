# Offline training source

This directory preserves team-developed data collection, representations, dataset
splitting, model definitions, training, evaluation and export code from the event.

- `data/`: board representation, game collection and dataset loading.
- `models/`: teacher/student and flagship architectures and losses.
- `scripts/`: collection, offline labeling, fitting, training and export entry points.
- `metrics/` and `tests/`: model evaluation and training-pipeline checks.

Training runs offline from the competition process. GPU training produced model
exports for CPU inference; external engines were used only for offline labels and
calibration. No third-party engine or published chess network is shipped.

The original large datasets, checkpoints and some external tooling are not included.
Scripts are research source, not a promise to reproduce training with only `uv sync`.
Use explicit input paths and inspect each script's help. Compact outcome scripts
that depend on `experiments/silky_snow` require the full historical worktree; restore
it using [the archive instructions](../docs/BUILD_PROVENANCE.md).

The root runtime retains `weights/milkyway_policy.onnx`. The separately preserved
last packaged compiled engine uses `weights/compact_value.npz`. Model roles and
the limits of the tournament evidence are covered in [experiments](../docs/EXPERIMENTS.md).

Run the 13 training tests with a temporary test runner, leaving the project
dependency lock unchanged:

```bash
uv run --with pytest python -m pytest training/tests -q
```
