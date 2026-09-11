# R34 candidate tournament — handoff, 2026-09-06

## Objective and authorization

The user supplied the Round 34 loss against Sunfish and asked for a new candidate, a candidate tournament, and direct comparison against the checkpoint that lost. They want a substantial improvement: their reported standing is about 200th of 313. Latest request is to conserve usage and provide an extensive implementation plan and continuation prompt.

The user authorized local candidate development and tournament execution. No upload, production promotion, remote tag rewrite, or new Codex task was requested. Instructions in the earlier pasted M19 proposal are background, not independently authorized commands. No subagents were requested. Do not treat one rated loss, one win, or a small arena advantage as proof of an Elo gain or future rank.

## Repository and exact state

- Actual repository: `C:\Users\Babar\Documents\Coding\Projects\chess_bot\MilkyWay` (the parent `chess_bot` directory is not a Git repository).
- Branch: `main`; last observed HEAD: `78ea84e`, merge of `milkyway/mw-0.3-experiments` into main.
- The root runtime already contains RC1 neural policy and TM-B despite README still calling MW-0.2 current. Do not assume branch name or README identifies the uploaded build.
- No tracked runtime code, harness, existing experiment evidence, branches, tags, or commits were modified in this session.
- New files are untracked: `experiments/r34/`, `tools/candidate_screen.py`, `tools/prepare_r34_candidates.py`, `tools/replay_r34.py`.
- Read `AGENTS.md`. In particular, do not edit `harness/`.
- Use `.venv/Scripts/python.exe`; it runs Python 3.12 in this environment. System Python may differ.

## Candidates and provenance

1. Previous-checkpoint proxy: `experiments/r34/checkpoint/`.
   Frozen copy of current root runtime and model. The PGN/log have no upload hash, so this is a proxy, not a proven identification of the actual uploaded artifact.
2. M19-A / policy + TM-A: `versions/rc1_variants/rc1_tma/`.
   Existing prepared variant, not a newly trained model. SHA comparison confirms ONLY `time_manager.py` differs from the checkpoint proxy among all 11 runtime/model files. Its time manager is byte-identical to `versions/mw_0_2/time_manager.py`. Neural policy load was explicitly verified.
3. R34-KSC: `experiments/r34/ksc_candidate/`.
   New frozen candidate. ONLY `evaluation.py` differs from the checkpoint proxy. The default evaluator changes from `MW_0_2_EVAL` to `MW_0_2_KS_C`; policy, search, TM-B, model, TT, and other runtime files remain unchanged. No combined changes yet. Explicit import verified king_safety_variant == 'C' and policy available.
4. Frozen historical baseline: `versions/mw_0_2/`.
   Must also be beaten or at least protected against regression before promotion. Beating rejected RC1 alone is insufficient.

`snapshots.json` records SHA-256 values for the checkpoint proxy and KS-C candidate. Tournament manifests record source/model hashes, opponent hashes, harness hashes, Python version, workers, clocks, seed, and FEN bank. Existing `experiments/m18/` and `experiments/m19/` remain unchanged.

The full runtime list is agent.py, constants.py, engine.py, engine_types.py, evaluation.py, move_ordering.py, root_policy.py, search.py, time_manager.py, transposition.py, weights/milkyway_policy.onnx.

## Active work — inspect before restarting anything

At the handoff inspection, BOTH tournaments were still running:

| Run | Launcher PID | Actual Python PID | Target |
|---|---:|---:|---|
| KS-C vs frozen checkpoint | 34668 | 28292 | 20 pairs / 40 games |
| M19-A vs root checkpoint proxy | 29804 | 41248 | 50 pairs / 100 games |

These PIDs are historical observations; verify process command lines before using them. The launcher and actual interpreter are not duplicate tournaments. The user interrupted a tool invocation, but M19-A's extension DID start and persisted after that interruption.

Do not launch another writer against an active output directory. Do not edit root runtime while the M19-A run is active: that run uses `--opponent .`. It would silently change the opponent for subsequently launched games. After all runs finish, verify root hashes still equal the frozen checkpoint. Future fresh runs should use the frozen checkpoint directory.

Read-only process check (sandbox access was denied; approved escalation was needed):

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and $_.CommandLine -match 'candidate_screen|replay_r34' } | Select-Object ProcessId,CommandLine | ConvertTo-Json
```

Completed pairs are written after every pair. A stopped run can resume with the same command once its old process and children have stopped. An unfinished pair is replayed; completed pair IDs are skipped. Reports are written only when that invocation reaches its requested pair count. Thus `report_40.json` remains a valid historical 40-game report while `pairs.json` has already grown beyond 20 pairs.

At last data read, these were the results; they are snapshots, not final outcomes:

- M19-A completed initial 40 games: **+17 =9 -14, 53.75%, paired 95% CI 43.75–63.75%**, no failed terminations. This is inconclusive.
- M19-A extension: 22 completed pairs / 44 games, **+18 =11 -15, 53.41%**; still running.
- KS-C: 5 completed pairs / 10 games, **+4 =2 -4, 50%**; still running. Completion-order partial results are not balanced samples and should not decide anything.

Exact resume commands, ONLY after confirming the respective run is no longer active:

```powershell
.venv/Scripts/python.exe tools/candidate_screen.py --agent versions/rc1_variants/rc1_tma --opponent . --out experiments/r34/tma_vs_checkpoint --pairs 50
.venv/Scripts/python.exe tools/candidate_screen.py --agent experiments/r34/ksc_candidate --opponent experiments/r34/checkpoint --out experiments/r34/ksc_vs_checkpoint --pairs 20
```

Changing opponent from `.` to the frozen directory changes the manifest, even if bytes match. The existing output directory intentionally rejects such changes. Preserve the command for that existing run or use a NEW output directory for a new experiment.

## Completed checks and artifacts

- Full root unit suite: **70 tests passed** using Python 3.12, about 50 seconds.
- Initial sandbox run failed only because a package-determinism temporary ZIP directory was inaccessible. Escalated repeat passed all 70 tests. Do not call the original error an engine reliability failure.
- Three added tools passed Ruff and targeted strict mypy with `--follow-imports=silent` after fixes. This is not a fresh repo-wide quality gate or proof that each frozen candidate passes its own full suite.
- No candidate submission ZIP has been built, tested, or uploaded in this session.
- Current competition contract/rules were fetched successfully with escalated curl after sandbox TLS failures. Temporary copies: `$env:TEMP\milkyway-agent-contract.md` and `$env:TEMP\milkyway-rules.md`. Re-fetch before relying on mutable competition requirements.
- R34 PGN and log copied into `experiments/r34/`.
- `tools/prepare_r34_candidates.py`: reproducible snapshot construction, refuses to overwrite existing snapshots. Do not rerun in the existing directory.
- `tools/candidate_screen.py`: paired tournament wrapper reusing the existing referee and M18 pair/bootstrap analysis. Default clock 10,000ms+100ms, four concurrent pairs, seed 20260906; supports up to 50 pairs.
- `tools/replay_r34.py`: fresh-process cold-TT diagnostic replays at the recorded pre-move clocks for Black moves 28, 31, 35, 36, 43, 47. Completed output: `experiments/r34/replay.json`.

## What R34 establishes and does not establish

Black lost by checkmate, not flag: 52 decisions, 0.8s init, 129.7s thinking across the game with increments, 16.3s left at the end, no stderr.

Do not call `31...Qd7 32.Rxe5 dxe5 33.Rxd7 Rxd7` a simple hanging queen. Black exchanged its queen for two rooks and retained a one-pawn material advantage using conventional values. White's queen and bishop then exploited the exposed king. Subsequent loss of pawns and rooks was decisive, but no independent reference-engine CPL analysis was performed.

Cold replay findings (one run, local hardware, simultaneous tournament load, no historical TT state):

| Black move | Checkpoint | Policy + TM-A | KS-C |
|---|---|---|---|
| 28 | Bg5, depth 4 | Bg5, depth 4 | Bg5, depth 4 |
| 31 | Qd7, depth 4 | Qd7, depth 4 | Qd7, depth 4 |
| 35 | Rf6, depth 5 | Rf6, depth 6 | Rf6, depth 6 |
| 36 | Rdc7, depth 5 | Rdc7, depth 6 | Rdc7, depth 5 |
| 43 | Rg5, depth 6 | Rg5, depth 6 | Rg5, depth 6 |
| 47 | Rgd5, depth 5 | Rgd5, depth 6 | Rgd5, depth 5 |

All three chose the same move at each of these six positions. TM-A sometimes reached one extra completed ply, but that did not establish better decisions. Some cold replays differ from the actual game, unsurprising without its TT/history and exact runtime speed. Scores are each engine's internal evaluations, not objective truth. No Stockfish executable was found on PATH; none was installed or shipped.

KS-C motivation: historical BENCHMARKS.md reported ~36.5% faster full evaluation and 57.5% in a 20-game ultra-fast screen. Those old results used legacy harness conditions and are hypotheses to re-test, not current qualification evidence.

## Implementation plan

### 1. Finish and integrity-check the current screens

Inspect live processes, pair files, and final reports. Let active runs finish unless the user asks to stop. Do not start extra heavy work merely while waiting; two four-worker tournaments already run on a machine reporting 16 logical CPUs. Host contention limits cross-run comparability. Paired colours help, but local clocks are not exact tournament-machine equivalence.

Validate unique pair IDs, expected target count, source/model/harness hashes, and absence of incomplete JSON. Use report_100.json for completed M19-A and report_40.json for completed KS-C. Recompute records and bootstrap directly from pairs.json if necessary. Retain the previous report_40.json as historical evidence.

Development decisions predeclared for remaining work:
- Any actual candidate reliability failure: stop qualification and diagnose. Do not silently count it as an ordinary loss or exclude it.
- KS-C below 45% at 40 games: reject this variant; otherwise extend to 100 before strength claims.
- At 100 games: below 48% reject; 48–52% neutral; 52–55% only modest encouragement; at least 55% is a reason for further testing, not proof of a major improvement.
- Report paired CIs, W/D/L, colour, phase and terminations. Interpret phase subgroups with their small sample counts.

KS-C extension command:

```powershell
.venv/Scripts/python.exe tools/candidate_screen.py --agent experiments/r34/ksc_candidate --opponent experiments/r34/checkpoint --out experiments/r34/ksc_vs_checkpoint --pairs 50
```

### 2. Compare surviving candidate with MW-0.2

Use a new directory and freeze the choice before looking at new results. The default runner chooses the same development positions, useful for paired comparison but NOT fresh holdout.

```powershell
.venv/Scripts/python.exe tools/candidate_screen.py --agent <winning-candidate-directory> --opponent versions/mw_0_2 --out experiments/r34/<candidate>_vs_mw02 --pairs 50
```

Do not substitute MW-0.2 for the required direct checkpoint comparison; do both. If candidates have close results, a direct candidate-versus-candidate match can help selection, but is still development evidence.

### 3. Test clock scaling early

For a survivor with convincing fast results, run medium clock first, then full clock. At minimum compare against the checkpoint proxy, and protect against regression versus MW-0.2. Use NEW output directories per opponent and time control. A changed seed or clock must never reuse saved results.

```powershell
.venv/Scripts/python.exe tools/candidate_screen.py --agent <winner> --opponent experiments/r34/checkpoint --out experiments/r34/<candidate>_medium_vs_checkpoint --pairs 20 --base-ms 30000 --increment-ms 300
.venv/Scripts/python.exe tools/candidate_screen.py --agent <winner> --opponent experiments/r34/checkpoint --out experiments/r34/<candidate>_full_vs_checkpoint --pairs 10 --base-ms 120000 --increment-ms 500
```

Repeat against MW-0.2 for the final prospective candidate. A 20-game full-clock result diagnoses gross scaling reversal; it cannot establish an Elo gain. Stop expansion if longer-clock results reverse materially. Do not run hundreds of fast games around a failing full-clock candidate.

### 4. If neither candidate improves materially, investigate before inventing more knobs

The user's desire for a much stronger engine is an outcome to seek, not evidence that a candidate is strong. It is acceptable to reject both and explain the measured outcome; do not rename a neutral build as an upgrade.

Prioritize bounded diagnostics:
1. Verify uploaded artifact identity if an accessible local ZIP/manifest exists. Keep uncertainty explicit if unavailable.
2. Replay the R34 sequence with persistent engine state at recorded clocks, reconstructing prior board observations as faithfully as possible. Contrast cold vs warm TT. Record actual time, completed depth, nodes, selected move, PV and score.
3. Use an available external engine only for development annotation, if found, to identify objective turning points. Never package someone else's engine or network. Without reference analysis, label conclusions as hypotheses.
4. Audit search tactical blind spots: current LMR can reduce quiet checking moves because it excludes parent in-check and captures/promotions but not child checks. Test a candidate that excludes checking moves from LMR, with a targeted regression and broad paired screen. Do not assert this caused R34 until measured.
5. Inspect king safety under queen-versus-rooks material imbalance. The current king-safety score fades with phase; test whether that undervalues exposed kings against a remaining queen. Any change needs general positions and mirrored-colour tests, not a hard-coded R34 move or FEN.
6. Profile evaluator/search to decide whether KS-C meaningfully increases nodes/depth in the relevant runtime. Do not use elapsed time from concurrent arenas as a clean microbenchmark.

Change ONE independent mechanism at a time, freeze hashes, run a 40-game kill screen then 100-game screen against the checkpoint. Keep the bank identical across early variants to reduce position noise. Build combined variants only after individual evidence, then test the combination itself.

Do not immediately retrain the neural network or implement TM-C plus policy gating together. Model attribution remains unproven. If TM-A succeeds, compare policy ON/OFF under identical TM-A and identical search/evaluation with at least 100 paired games. If it is neutral, diagnose model integration/data before spending GPU time.

### 5. Make final qualification honest

The existing 200-position bank was already exposed in M18. Reshuffling it with a new seed does not create untouched evidence. The current runner's first 20 positions are a shuffled prefix, not exactly 25/50/25 phase-balanced; its initial M19-A phase counts were 4 opening, 9 middlegame, 7 endgame pairs. Preserve those facts, do not retroactively call this a perfectly stratified kill screen.

Before final qualification, add explicit input-FEN-bank support or a separate driver. Create a new legal development-independent set with provenance and no overlap with prior tuning positions. Freeze a 100-pair screen and independent 100-pair confirmation set before running. Support >50 pairs in a deliberate runner change; the present script rejects >50. Do not blindly invoke tools/m19_tournament.py: it is substantially a copied M18 full runner, retains RC1 naming and M18 assumptions, and was not audited as a correct M19 protocol. Review its software-gate and cached-result semantics first.

Prospective promotion target: at least 55% over a substantial direct-checkpoint sample with paired lower 95% CI above 50%, independent confirmation, no reliability failures, no material regression against MW-0.2, and no longer-clock reversal. Precommit exact thresholds and stopping rules BEFORE new confirmation results. Higher targets such as 60% are appropriate aspirations for a large gain, not guarantees. Winner selection over many variants requires independent confirmation to limit selection bias.

### 6. Software and package gates for the actual finalist

- Run full Ruff, strict mypy, unit suite, harness-rule tests and historical rated regressions.
- Ensure tests actually import the finalist's modules, not accidentally the root checkpoint. Run in an isolated candidate context and record imported __file__ paths.
- Add meaningful regression tests for new search/eval behavior, mirrored positions and board restoration where appropriate.
- Run time probe, fuzz, long-game stress, ONNX inference and package determinism tests on the candidate.
- Build and extract a ZIP containing only runtime files plus the team's model, agent.py at root. Build twice and compare bytes/hashes using the existing package workflow; do not modify the harness to fake determinism or acceptance.
- In Python 3.12, import the extracted artifact, verify policy/evaluator/time-manager identity, and play actual harness smoke games as both colours.
- Record all dependency versions, Python version, source/model ZIP hashes and uncompressed size. Validate against current official competition rules.
- Recheck hashes after tournaments and tests. Only a tested immutable artifact can be described as the finalist.
- Do not overwrite submission.zip or upload/promote without the user's corresponding authorization. A local clearly labelled candidate ZIP is fine.

### 7. Reports, cleanup and reproducibility

Write experiments/r34/REPORT.md with candidate definitions, provenance, completed tournament tables, paired CIs, phase/colour results, reliability, full-clock evidence, loss diagnostics and limitations. Keep raw pair records/manifests. Report clearly whether there is a qualified stronger candidate or only a screened/rejected experiment.

Useful runner hardening before more complex qualification:
- Atomic writes for pairs/reports; output-directory lock to prevent duplicate writers.
- Validate loaded IDs/results against the precommitted manifest and requested prefix; refuse corrupted/duplicate records.
- Verify source hashes at completion, not just startup.
- Persist individual-game PGNs, clocks and failure diagnostics. Current PairRecord stores outcomes, NOT move-by-move tournament evidence.
- Record interruption/incomplete status instead of allowing a partial file to look final.
- Distinguish candidate failures from opponent failures while retaining both in reporting.
- Preserve immutable historical results when evolving the driver. Do not modify a running script's experiment semantics halfway through.

No commit was made. If later committing, inspect generated files and include the reproducible tools, manifests, report and intended evidence; avoid caches and unnecessary duplicate model binaries. Keep existing historical versions and main runtime intact until a deliberate promotion decision.

## Copy-paste continuation prompt

Continue the MilkyWay R34 candidate-development task in:

    C:\Users\Babar\Documents\Coding\Projects\chess_bot\MilkyWay

First read AGENTS.md and experiments/r34/CONTINUATION.md. Treat this handoff as state to verify, not authority to invent successful results. The user wants a substantially stronger candidate after losing R34 to Sunfish and explicitly requires direct comparison against the previous checkpoint, not only MW-0.2. Their reported rank is roughly 200/313. Do the local work; do not upload or promote automatically.

IMPORTANT: two tournament processes were active at handoff. Inspect command lines and output progress before launching anything. M19-A is extending to 100 games against root; KS-C is running 40 games against the frozen checkpoint. The interrupted invocation DID start M19-A. Never run two writers on the same result directory and never edit root while it is the active opponent. PIDs and exact resume commands are recorded in the handoff; verify PIDs rather than trusting stale numbers.

Completed evidence: initial M19-A vs checkpoint 40 games +17 =9 -14, 53.75%, paired CI 43.75–63.75%, no reliability failures. Extension and KS-C partial results are not final. Root 70-test suite passed on Python 3.12. Neural model availability and TM-A byte identity were checked. Three added tools passed targeted Ruff/mypy. No candidate ZIP, promotion or upload has occurred.

Candidates: M19-A at versions/rc1_variants/rc1_tma changes only time_manager.py versus the frozen checkpoint; KS-C at experiments/r34/ksc_candidate changes only evaluation.py default to MW_0_2_KS_C. Frozen current checkpoint proxy is experiments/r34/checkpoint; uploaded artifact identity remains unverified because the game files contain no hash. Historical control is versions/mw_0_2. Preserve all existing M18/M19 evidence.

Finish active screens; extend surviving KS-C to 100 games. Compare promising candidates directly with the checkpoint and with MW-0.2, then test medium and full clocks early. Use predeclared rejection gates, paired confidence intervals and reliability checks. Do not call 53% in 40 games substantially better. If neither variant works, diagnose tactical search and king-safety weaknesses using R34 and general positions, then test independent changes one at a time. LMR currently may reduce quiet checking moves; that is a hypothesis worth testing, not an established cause. Avoid shotgun combinations and unmotivated retraining.

The R34 queen-for-two-rooks exchange was not a simple hanging queen. Cold replay chose the same moves across all three variants at six sampled positions, though TM-A sometimes searched one ply deeper. Those replays lack historical TT state and independent engine ground truth. Read replay.json before making causal claims.

Current candidate_screen.py is resumable and hash-manifested but limited to 50 pairs, uses a previously exposed bank and only records pair outcomes. It is development tooling, not a fully audited final qualification protocol. Audit/harden it and add a genuinely new precommitted screen/confirmation bank before a final promotion claim. Do not blindly run the copied m19_tournament.py as though its name guarantees correct M19 behavior.

Run final software gates against the actual candidate modules and extracted package, including Python 3.12, real harness smoke games, time/fuzz/regression checks and deterministic packaging. Produce a consolidated REPORT.md and a clearly labelled local candidate artifact only if warranted. Be candid if no substantial improvement is established. Save enough raw evidence and exact commands for reproducibility. Conserve model usage with bounded local scripts and meaningful updates; do not spawn subagents or create new tasks unless asked.
