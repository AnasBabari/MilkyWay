# MilkyWay / Astralix / Search V2 — implementation handoff

Snapshot: 2026-09-09. This is a continuation plan, not a promotion report.

## 1. Objective and authoritative acceptance criteria

Deliver a verified new `agent.zip` containing our own stronger chess agent. The latest user clarification is **at least 60% SCORE against the exact live silky_snow candidate**. Score = (wins + half draws) / games. Report actual win rate separately. Old 70% actual-win, 70% score, and incorrectly described 55% “10-point improvement” language is superseded. 55% is only the current development parent/challenger screening threshold.

The candidate must also beat the other candidates. Current independent confirmation protocol requires the opening-pair bootstrap two-sided 95% lower score bound to exceed 50% against each challenger (20,000 resamples, seed 2026090823). Do not substitute a positive point estimate or transitive comparison for that gate.

Final confirmation: 100 games / 50 reversed-colour pairs per opponent, 120,000 ms + 500 ms, one worker per comparison, fresh independent openings, exact frozen runtime hashes, zero reliability failures. Live comparison first; after it passes, at most two challenger comparisons concurrently. No training or development compilation during confirmation. No favourable early stopping.

Stockfish Skill 7 is diagnostic, not a mandatory qualification target. Offline engines may generate training labels, training opponents, and diagnostics. Never include third-party engine code, ports, binaries, published chess-network weights, or runtime engine-evaluation/move lookup databases in the submission. No upload is authorized. No subagents. Preserve dirty work and never edit harness/.

## 2. Workspace and operational state

- Repository: `C:\Users\Babar\Documents\Coding\Projects\chess_bot\MilkyWay`.
- Shell: PowerShell. The parent `chess_bot` directory is not this Git repository.
- Recorded branch/main baseline: 834ceb88fa1f32cd242431bc1be171f9ecaaad7a. Recheck current HEAD before claiming it remains unchanged.
- Dirty tree is intentional. Latest status includes engine.py, engine_types.py, evaluation.py, search.py, time_manager.py, tests, training, and many untracked experiments. Do not reset, clean, restore, or overwrite these broadly.
- `.venv/Scripts/python.exe`: repository Python 3.12. `training/.venv`: GPU training environment, previously verified torch 2.6 cu124 / RTX 2060. No training is currently needed.
- Windows subprocess pipes and HTTPS encountered sandbox restrictions. Approved escalated local execution worked. Use the tool approval mechanism when necessary; do not disable TLS verification or rewrite the harness.
- Poll exact process/session handles. A quiet poll is not failure. Never restart from a stale state file alone, and never kill by process name. Verify identity and descendants before any termination.
- No recurring app heartbeat is known active. The previous heartbeat was absent; do not claim it exists. The current tournament continuation is an actual local Python process.

## 3. Verified current state — start here

**No qualified candidate. No new agent.zip.**

Selected development candidate: `experiments/search_v2_combined_01`, mechanism staged quiescence generation plus late-move reductions (LMR). It is frozen, not promoted.

Completed parent comparison: `experiments/search_v2/combined_parent_12s_50g`.

- 50 games, 12s + 0.1s, 3 workers, seed 20260906, paired colours.
- 29 wins, 10 draws, 11 losses = 34/50 points = **68% score**, 58% actual wins.
- White 74% score, black 62% score.
- Zero failed terminations. Final independent PGN/clock/runtime/harness hash audit passed.
- `combined_parent_final_audit_01.json` and `report_50.json` preserve the evidence.
- Parent session 32785 completed with exit 0. Do not restart it.

**Active continuation session: 20981**, confirmed live during this handoff. It has advanced to `screen_running_live`.

- Driver: `tools/continue_combined_campaign.py`, invoked as `python -m tools.continue_combined_campaign`.
- Authoritative current state: `experiments/search_v2/combined_continuation_01.json`.
- Active comparison: `experiments/search_v2/combined_live_12s_50g`, combined vs exact live `experiments/silky_snow`.
- Same development conditions: 50 games, 12s + 0.1s, 3 workers, screen bank, seed 20260906, raw recorded games.
- At snapshot, manifest exists and 2 games are saved. This is not a score claim or a completed gate.
- Parent run passed; both sequential clock replays completed; the live screen started automatically.
- `combined_campaign_01.json` is an older launch summary. Prefer `combined_continuation_01.json` for current progress.

The driver continues sequentially through live, PVS, RL, staged, LMR, and aspiration if each preceding gate passes. Live needs 60% development score; the other screens need 55%. Every full match is audited. A rejected gate or process/audit error leaves an attention/rejection state for further work. It does not retrain, create a new candidate, run final confirmation, promote, or build a ZIP.

## 4. Earlier campaign and why the approach changed

The initial Astralix direction combined an own compact neural evaluator with classical search. Earlier data work built balanced examples and corrected a degenerate dataset whose value targets were all +1.0. Offline Stockfish MultiPV labelling and joint policy/value training produced a usable own network, but the integrated Astralix v1 regressed. Historical small SF6 tests scored 37.5% for a classical/depth baseline and 8.3% for full Astralix. These are historical diagnostic results under their recorded conditions, not current qualification.

The old 60s campaign also failed its then-declared live/SF7 gates. Parent diagnostics favoured ordered search (61%) and an RL weights-only variant (57%), but target comparisons were rejected, several by mathematical futility. Preserve `compact_cycle_01/campaign_closeout_60s_01.json` and `CAMPAIGN_REJECTION_60S.md`; never resume their stopped runs or pool them with later screens.

Search profiling found 91.53% of nodes were quiescence work, and legal move generation substantially exceeded searched children. That justified original search engineering before further blind RL. Development screens were accelerated to 12s + 0.1s with 3 workers. Fresh per-game processes still incur roughly 20–25 seconds of Numba initialization per agent; actual throughput varies. Do not promise a fixed finish time or enable persistent Numba caches in the agent to evade the platform environment.

## 5. Completed Search V2 development results

All results below are 50-game paired development screens at the fast clock, not final confirmation.

| Candidate | vs ordered parent | vs live silky | vs PVS | vs RL |
|---|---:|---:|---:|---:|
| LMR | 24W10D16L, 58% | 35W8D7L, 78% | 25W12D13L, 62% | 27W8D15L, 62% |
| Staged | 28W9D13L, 65% | 41W5D4L, 87% | 35W6D9L, 76% | 26W11D13L, 63% |
| Aspiration | 22W2D26L, 46%, rejected | not run | not run | not run |
| Combined | 29W10D11L, 68% | running | queued | queued |

Original nine completed screens were independently audited in `verified_development_results_01.json`. Staged beat LMR directly 23W10D17L = 56%, with a paired score interval of 44–68%. It won the selection tiebreak, but that interval did not establish population superiority.

## 6. Staged disqualification and the new clock evidence

Staged's full-clock confirmation was stopped at 35 recorded games: 14W6D15L = 17/35 points = 48.57%, with one flag termination. That reliability failure disqualified the run regardless of score. The score alone was a partial result, not mathematical impossibility of reaching 60% after 100 games.

Evidence: `confirm_staged_live_120s_100g/futility_decision.json`; failed game `games/fresh_confirm_009_white.json`. The filename says futility but the recorded reason is reliability disqualification. Do not resume this run. `confirmation_campaign_01.json` was corrected from stale running status to disqualified. Inspect actual lock existence if needed; older narratives conflict over whether it was retained or removed.

The PGN showed 55.751 seconds remaining before the next white request after 24...Nf6. Code inspection found a deadline check every 128 nodes and a normal hard budget far below the remaining clock. This does not establish a cause. Do not assume low-clock exhaustion, an engine hang, OS suspension, or an infrastructure fault without further evidence.

New diagnostic: `tools/replay_clock_failure.py`, unchanged sandbox, historical requests and clocks, plus the failed position. It records runtime hashes, import time, per-request elapsed time, legality and stderr. Ruff and targeted strict mypy passed.

Both replays completed all 17 requests with no recorded failures:

- Staged: import 22.950s; formerly failed request returned legal `e4c2` in 4.606s.
- Combined: import 23.486s; same request returned legal `e4c2` in 2.235s.
- Evidence: `staged_flag_replay_01.json/.log` and `combined_flag_replay_01.json/.log`.

The replay did not reproduce the flag. It is a diagnostic, not exoneration or full reliability proof. Different returned moves may alter history synchronization, and opponent thinking delays were not replayed. Staged remains disqualified. Full-clock testing remains essential for combined.

## 7. Combined implementation and verification

Combined was built in a new isolated runtime, preserving both frozen parents. It merges staged capture-focused quiescence generation and the previously tested LMR block. LMR applies to later quiet non-checking moves in narrow-window nodes, with full-depth re-search after alpha improvement. Staged generation preserves check evasions, promotions, terminal handling, and stalemate detection.

Pre-freeze verification (`combined_verification_01.json`): 30 fixed-depth positions; 18,950 reductions and 37 re-searches; nodes 1,582,734 to 1,038,971 (34.4% fewer); two move disagreements; zero reported low-clock failures; 40-ply legal self-play sequence. The reported -3cp difference compares the candidates' own search scores, not an independent oracle measure of move loss. Do not overstate it as proof of tactical quality.

Frozen manifest: `search_v2_combined_01_manifest.json`; playing runtime also has `manifest.json`. All 12 runtime file hashes were reverified before the parent screen. `combined_search.py` SHA256: c9e4806ff7eac071e1bbe43c8f5dffe7ff63c1a94a973dbbf9c5e89e052a779f.

Static package preflight passed: exact frozen members, 178,701 bytes unzipped, allowed imports, no native binary members or enabled cache/parallel flags detected. Evidence `combined_package_preflight_01.json`. This AST check does not prove all legal provenance, platform resource compliance, or archive correctness.

## 8. Next implementation sequence

### A. Finish current development automatically

1. Poll session 20981 and read combined_continuation_01.json. Do not launch duplicate screens.
2. For each completed screen inspect its full report and independent audit: 50 games, 25 complete pairs, correct clocks, exact candidate/opponent/runtime/harness hashes, all raw games retained, zero failures.
3. Keep live score and actual wins distinct. Apply 60% score vs live and 55% screening score vs each challenger.
4. If a match fails, preserve it and diagnose the mechanism or time scaling before changing the candidate. Create a new isolated variant; never mutate a tested runtime.
5. If the driver stops unexpectedly, inspect error, log, child identity and output manifest. Never restart just because a poll returned no output. Existing output directories require explicit evidence-aware recovery.

### B. Establish full-clock reliability and strength scaling

Fast-clock superiority did not transfer for staged. Before spending another full confirmation campaign, predeclare a separate full-clock DEVELOPMENT screen at 120s + 0.5s on already exposed development positions, with raw games and exact frozen runtimes. Keep it separate from fast screens and independent confirmation. Choose and record its fixed game count and diagnostic stop rules before launch; do not silently call it qualification.

Investigate any flag with request FEN, clock, elapsed time, import time and retained logs. Use external diagnostic tools; leave harness and frozen playing code unchanged. If a fix is required, create a new candidate, verify it and rerun relevant comparisons. Do not assume faster search fixes every timing failure.

### C. Prepare a NEW independent bank and protocol

The old staged confirmation bank is exposed. Never reuse it as unseen confirmation for combined or a subsequently selected runtime.

An initial exclusion index contained 903,252 placements. Another session refreshed it to 909,786 placements and 1,597 provenance entries after combined creation; old files were archived as superseded. Revalidate current SQLite integrity, source hashes and coverage before relying on it. Include all new development/replay/full-clock data and any new training positions.

Use versioned new bank/protocol filenames and seeds. Existing generation/finalization scripts contain old campaign paths; inspect and parameterize or copy to a new version without modifying old evidence. Generate openings using offline-only engine trajectories and fixed balancing rules, never candidate performance. Audit legal replay, uniqueness, exact and colour/rank-reflected placement exclusions, all source hashes, and post-snapshot game overlap. Freeze the new bank before any qualifying match.

Create a combined-specific confirmation protocol. Existing CONFIRMATION_CAMPAIGN_PROTOCOL.json describes the staged campaign and old bank despite its useful gate values. For combined the challenger roster is ordered, PVS, RL, staged, LMR and aspiration, plus live silky. Record exact runtime hashes and the selection rationale before starting.

### D. Run independent confirmation

100 games per opponent, 50 reversed-colour pairs, 120s + 0.5s, one worker each. Live first, requiring >=60% score and zero failures. If passed, at most two challenger matches concurrently. Each challenger must satisfy the predeclared paired-bootstrap lower-bound gate. Preserve all games, clocks, manifests and failures. No early positive stop; no strength claims from a partial run.

If confirmation fails, the goal remains active. Return to measured development and use a newly independent bank after tuning/reselection. Do not lower the gate or retrospectively exclude bad openings.

### E. Package only after qualification

Refresh official rules and contract; 2026-09-09 copies match 2026-09-08 hashes. Current files are competition_rules_20260909.md and agent_contract_20260909.md. Follow AGENTS.md.

Run applicable lint/type checks, meaningful unit/legality/fuzz tests and platform-style full-clock reliability checks. Distinguish existing dirty-tree failures from candidate failures without ignoring relevant defects. Verify own-code/model-training provenance and include no offline engines/data lookup tables.

Build a deterministic ZIP from the exact qualified runtime, with agent.py at its root. Preserve the existing root agent.zip first; it is not interchangeable with agent_silky_snow.zip. Extract into a clean directory, compare every runtime member hash to the qualified manifest, check size/imports, and run smoke games from the extracted artifact using the unchanged harness. Record ZIP SHA256 and reproducible build recipe. Produce final WDL/conditions/uncertainty/reliability/provenance report and link the new agent.zip. Do not upload.

## 9. When to use further training

Keep reinforcement learning against stronger Stockfish levels available if controlled evidence shows an evaluation weakness. It is not the immediate next action while the frozen combined tournament runs. Use own network initialization, balanced labels/results, legal position generation, held-out validation, queen/material extreme probes, single-writer outputs and versioned checkpoints. Compare weights-only variants against the same frozen search before combining changes. Never mix search tuning and network tuning in one unexplained trial. Stockfish difficulty labels and any Elo mappings must not be treated as verified playing ratings.

## 10. Completion audit

The goal is complete only when the final candidate satisfies the agreed live gate, all challenger gates, full-clock reliability, exact frozen-runtime provenance, package compliance, clean extraction/hash verification, extracted-artifact smoke tests, and a delivered new agent.zip. Current evidence establishes only the combined parent development pass and two successful diagnostic replays. Everything else remains pending or running.

Update the active goal to complete only after inspecting evidence for every requirement. A running game is a verified wait, not a blocker. Leave the goal active while testing/development continues.
