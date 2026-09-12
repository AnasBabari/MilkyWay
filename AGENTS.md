# Working on MilkyWay

AI Chessathon 2026 is complete. This is a portfolio and reference project. Preserve
engine behavior during documentation and repository maintenance; strength changes
need a separate experiment and evidence.

## Entry points and provenance

- The root Python engine exposes `agent.get_move(fen, time_left_ms) -> str`.
- `versions/final_packaged/` is the immutable source extracted from the last
  documented compiled TM archive. It differs from the root engine.
- Read `docs/BUILD_PROVENANCE.md` before making claims about submissions or models.
- Full research history is at `aichessathon-2026-final-workspace` and
  `archive/aichessathon-2026-full`. Never rewrite or squash that history.

## Rules and runtime

Fetch the official sources before answering questions about current limits or
allowed submissions: https://aichessathon.com/docs/agent-contract.md and
https://aichessathon.com/docs/rules.md. Historical constraints are summarized in
`docs/POSTMORTEM.md`; do not assume a future event uses them unchanged.

Runtime code stays readable Python source, single-process and CPU-only. Do not
introduce network calls, external engine processes, borrowed engines or borrowed
networks. Offline training and calibration are separate. Ship required weights
with a package and load them during import; do not download at runtime.

## Maintenance and verification

- Do not edit `harness/`; it mirrors the competition protocol and clock.
- Do not edit frozen `versions/` snapshots merely to satisfy style checks.
- Python 3.12; annotated maintained source; Ruff and strict mypy. Mypy targets Linux.
- Keep tests, dependency versions and runtime module boundaries unless the task
  explicitly requires changing them. Never delete a test to make a gate pass.
- Run `uv sync`, `uv run ruff check .`, `uv run mypy`,
  `uv run python -m unittest discover tests`, `make gate`, and `make zip`.
- On Windows without Make, run the corresponding commands from the Makefile.
- Package smoke tests exercise extracted source. A fresh root package is not the
  archived TM build, and local smoke does not establish platform acceptance.
- Keep generated ZIPs, checksums, logs and training outputs ignored. Publish release
  assets or explicitly document the reason for tracking an artifact.
- Do not read `HARNESS_SEED` in agent runtime; it is for local baselines only.
