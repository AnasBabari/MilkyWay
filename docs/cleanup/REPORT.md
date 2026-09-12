# Portfolio cleanup report

This report records the final cleanup of `AnasBabari/MilkyWay`. The archive tag
and branch were created at pre-cleanup commit `114cfa7`, pushed and verified before
any removal. All source, experiments and assets from that tracked state remain
reachable. The initially clean checkout contained no untracked or ignored files.

## Files and structure

The cleanup removed 3,553 historical files from the maintained tree and relocated
14 paths, including the last documented ZIP/checksum. The latter are published
as release assets rather than tracked again. Frozen extracted source is retained.
The complete path lists are in [FILE_CHANGES.json](FILE_CHANGES.json); the original
path/size inventory is [INVENTORY_BEFORE.json](INVENTORY_BEFORE.json).

- Removed intermediate archives/checksums, unused flagship ONNX models and their
  external data, raw experiment outputs, duplicate candidate trees, obsolete
  launchers, logs, the evaluator backup, stale manifest and unused neural wrapper.
- Moved benchmarks and development history under `docs/`; replaced the old
  Silky-Snow report with a closed retrospective under `docs/experiments/`.
- Moved rated-game and regression narratives under `docs/`, preserving test FENs.
- Rewrote README, training/tool guides and contributor instructions. Added the
  architecture, experiment narrative, postmortem, provenance and size audit.
- Removed `CLAUDE.md`, a redundant helper symlink to `AGENTS.md`, and the duplicated
  starter ideas document. `AGENTS.md` remains for repository-specific maintenance.
- Preserved all tests, baselines, harness files and all eleven root runtime modules
  byte-for-byte. Added annotations and lint fixes only to offline research tools.

```text
.gitattributes             preserve exact archived package member bytes
.github/
artifacts/final/            release notes; ZIP/checksum are ignored local copies
baselines/
docs/
experiments/
harness/
tests/
tools/
training/
versions/
weights/
.gitignore
AGENTS.md
LICENSE
Makefile
README.md
pyproject.toml
uv.lock
agent.py
constants.py
engine.py
engine_types.py
evaluation.py
fast_eval.py
move_ordering.py
root_policy.py
search.py
time_manager.py
transposition.py
```

Ignored `.venv/`, caches, `scratch/` and generated `submission.zip` are local
verification products, not public repository content.

## Runtime and models

The root ONNX policy model is 5,268,829 bytes and remains default-enabled when
loadable. The last documented TM package instead contains a 56,644-byte compact
value NPZ, preserved in `versions/final_packaged/`. Its 12 original package
members are hash-checked. Experimental ONNX variants live only in history.
See [build provenance](../BUILD_PROVENANCE.md) for the source/archive discrepancy
and the unestablished final successful upload identity.

## Validation

- `uv sync`: passed on Python 3.12.14; dependency versions unchanged. The lockfile
  changes only the local project identity to `milkyway-chess-engine` 1.0.0.
- `uv run ruff check .`: passed. The immutable final-package source is explicitly
  excluded; maintained source and all tests remain checked.
- `uv run mypy`: passed, 118 files, strict Linux target. This avoids checking Linux
  signal APIs against Windows stubs without modifying the harness. Optional
  offline ingestion libraries have scoped missing-stub configuration.
- `uv run python -m unittest discover tests`: passed, 87 tests in 40.587 seconds.
- Supplementary offline training tests: 13 passed in 26.28 seconds using
  `uv run --with pytest python -m pytest training/tests -q`. Initial attempts with
  unittest and the bare pytest executable exposed the optional runner/import-path
  requirements; the documented module invocation passed without lockfile changes.
- `make gate`: Make is unavailable on this Windows host. Its three exact commands
  were run directly: Ruff, mypy and two 5-second-base random-opponent games. Both
  games ended in checkmate wins; no failed terminations.
- Root package generation and extracted-package smoke: passed as both colors,
  both reaching the harness smoke ply cap without a failed termination. The ZIP
  was 4,891,210 bytes compressed / 5,395,412 bytes uncompressed.
- `uv lock --check`: passed; relative Markdown links and all eleven root-runtime
  hashes passed the cleanup audit.
- Exact historical TM release archive: extracted-package smoke passed as both
  colors, reaching the smoke ply cap without failed terminations. All twelve
  original members match the ZIP, local extraction and committed Git blobs.
- Hosted CI: [run 34725029935](https://github.com/AnasBabari/MilkyWay/actions/runs/34725029935)
  passed all jobs at code commit `49f9c35`: Linux `make gate`, 87-test discovery
  and `make zip`, plus Windows and macOS harness games on Python 3.12.
  Later closeout edits only update documentation and audit results.

These checks establish local reliability, not a new strength result or platform
acceptance. The unchanged local harness still uses its own 90-second init budget;
the retrieved event contract specifies 30 seconds for the final stage.

## GitHub and branches

Description changed to “Competition chess engine built for AI Chessathon 2026 —
alpha-beta/PVS search, handcrafted evaluation and ONNX root policy experiments.”
The event homepage was retained. Topics: `python`, `chess`, `chess-engine`,
`artificial-intelligence`, `alpha-beta`, `onnx`, `machine-learning`, `hackathon`,
`search-algorithms`.

Published [AI Chessathon 2026 Final Build](https://github.com/AnasBabari/MilkyWay/releases/tag/aichessathon-2026-final-build)
with the exact ZIP and checksum. GitHub's uploaded-asset digest matches the local
verified ZIP hash. Its annotated release tag points at the original pre-cleanup
commit. Release notes explicitly distinguish the last documented package from the
unestablished final platform upload.

All three remote development tips were verified as ancestors of the archive:

| Branch | Tip | Recommendation |
| --- | --- | --- |
| `milkyway/core-engine` | `c3518f7` | May be deleted after owner review |
| `milkyway/m16-eval-tuning` | `4c769e5` | May be deleted after owner review |
| `milkyway/mw-0.3-experiments` | `559453a` | May be deleted after owner review |

No remote branch was deleted. The Linux gate and Windows/macOS harness jobs remain
configured for Python 3.12; Linux CI now also runs the full unit suite and package
smoke. Manual dispatch was added and used to obtain the successful hosted run.
Two concurrent remote commits with no net tree change were merged normally before
pushing; neither their history nor the cleanup history was rewritten.

## Size and narrative

Tracked content fell from 344.2 MB to approximately 7.7 MB (about 97.8%). The
84.00 MiB historical Git pack remains: normal cleanup does not shrink clones.
[HISTORY_SIZE.md](HISTORY_SIZE.md) details ZIP/ONNX storage, the largest objects
and a separate, unexecuted history-rewrite proposal.

The README presents the event record and engine pipeline first, then measured
performance work, the keep/revert method and honest neural evidence. The
postmortem explains clock failures, rejected candidates, invalidated experiments,
the source/package divergence and future research directions. It claims no
placement or awards and records the owner's final +47 =12 -43 result and peak
event Elo 1556.

No speculative chess-strength change, engine rewrite, harness edit, test deletion,
history rewrite, force-push, squash or remote-branch deletion was performed.
