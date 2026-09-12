# Measurement and analysis tools

Run tools from the repository root using `uv run python tools/<name>.py --help`.
Useful entry points include `benchmark_eval`, `benchmark_search`, `diff_eval`,
`profile_search`, `fuzz_positions`, `time_probe`, `paired_arena`, `candidate_screen`,
`recorded_pair`, and the rated-game analysis tools.

M18/M19 and confirmation utilities preserve historical experimental protocols;
they do not imply an active promotion campaign. Supply explicit agent and output
paths. Historical candidate inputs live in the archive snapshot. Offline Stockfish
calibration tools require a separately installed executable and never ship it.

One-off launchers and probes tied to removed experiment directories are preserved
in the archive rather than exposed as maintained commands. `verify_search_freeze`
checks MW-0.2 reference presence by default; strict mode compares root source with
that earlier baseline and is expected to report differences after later revisions.
