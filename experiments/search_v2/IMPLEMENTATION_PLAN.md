FINAL GATE CONFIRMED BY USER: >=60% SCORE against exact live silky_snow at independent120s+0.5s confirmation,100games. This supersedes all70%-actual-win and ambiguous55%/+10point final targets below. Other-candidate superiority and reliability/artifact gates remain. See TOURNAMENT_PROTOCOL.json.

LATEST USER REVISION: prioritize >=70% ACTUAL WINS against exact live silky_snow, plus superiority over the three current compiled challengers in the candidate tournament. SF7 is diagnostic only; the older >=50% SF7 gate is withdrawn. Development60s+0.5s/50games; independent confirmation120s+0.5s/100games per opponent. See TOURNAMENT_PROTOCOL.json. All older score-based live gates below are superseded.

# Search V2 implementation and continuation plan — 2026-09-08

This plan supersedes the older repeated current-state sections in compact_cycle_01/IMPLEMENTATION_PLAN.md and CONTINUATION_PROMPT.md. Historical evidence stays preserved. Search-first development is now authorized; blind RL/value cycling is paused.

## Goal and protocol

The same frozen candidate must earn at least 70% score against exact silky_snow and at least 50% actual wins against Stockfish Skill7, then pass independent confirmation and artifact/reliability checks before a new promoted agent.zip is created. Score is (W+0.5D)/N; actual wins are W/N. No upload is authorized. The target remains unachieved.

Development comparisons: 60,000ms + 500ms, 25 paired openings / 50 games, one worker per comparison, reversed colours, fixed bank and seed 20260906, recorded games. Full confirmation: predeclare 50 pairs / 100 games per opponent at actual platform 120,000ms + 500ms, a new independent bank, controlled load, no concurrent training/compilation. Do not pool clocks, adapt sample size to a favourable partial result, or call development screens confirmation.

Stockfish remains the recorded binary with Skill7, Threads1, Hash16 and unchanged baseline clock adapter. First compute max(0.05,min(1.0,(time_left_ms/1000)*0.05)), then min(that,max(0.001,time_left_ms/2000)). Healthy 60s and 120s clocks both yield 1s per move. No fixed-movetime override, invented Elo, inferred depth or weakening of the opponent.

## Verified work and current rejection

Repository HEAD 834ceb88fa1f32cd242431bc1be171f9ecaaad7a; preserve extensive existing dirty/untracked work. Never reset the tree or edit harness/. No subagents. Repository interpreter is .venv/Scripts/python.exe; GPU interpreter training/.venv/Scripts/python.exe, currently unnecessary.

- Own compact residual model and guarded terminal-outcome learning already exist. Offline validation improved, but strength did not reach the gates. The latest RL candidate changes only the compact weights relative to PVS. This is terminal-outcome learning with supervised replay, not policy-gradient training.
- Original compiled board/evaluation/search passed recorded perft, legal-transition, evaluation-parity, reference-search, TT/PVS, agent-history and deadline checks. Refer to each frozen candidate's verification files; these are scoped tests, not a full repository/platform certification.
- The three candidates are compiled_pvs_01, compiled_ordered_01 (quiet ordering delta) and compiled_sf7_rl_01 (weight-only delta). Exact flagship is experiments/silky_snow, matching agent_silky_snow.zip; the unrelated existing root agent.zip must be preserved.
- All three SF7 runs were already stopped after mathematical futility: PVS 2W/30 games, maximum 22/50 wins; ordered 6W/33, maximum 23; RL 3W/35, maximum 18. Required wins: 25.
- Ordered/silky was already stopped at 10W3D14L, 11.5 points in 27 games, maximum 34.5/50. Required points: 35.
- This audit independently recounted and stopped PVS/silky at 17W6D16L (20 points in 39 games, maximum31) and RL/silky at 17W3D20L (18.5 points in40, maximum28.5). Exact root command lines, descendants and preserved orphan records are in their futility_decision.json files. Both surviving parent owners were verified alive afterward.
- Parent diagnostics remain live: ordered vs PVS and RL vs PVS. Snapshot06 observed 36 games each, respectively 18W8D10L and18W5D13L. These counts are observations, not current truth. They have no promotion futility gate and must be allowed to settle.
- All recorded games in snapshot06 passed the existing hash/PGN/clock auditor. Stopped screens are truncated evidence; do not compare their raw partial percentages as if they used an identical completed sample.

## Phase 1 — finish the campaign honestly

1. Recheck writer.lock, actual PID and full command line; old terminal session IDs are stale after an earlier dead-writer recovery. Live-at-audit owners: 31880 ordered/parent, 37948 RL/parent. PID identity must be revalidated before any action.
2. Let both parent comparisons reach 25 committed pairs and report_50.json. If a process exits unexpectedly, distinguish complete, failed and stalled; never erase results or silently turn failure into completion. Do not resume any directory containing futility_decision.json.
3. Audit all eight comparisons with existing read-only tools, including orphan completed games separately from committed pairs. Validate frozen runtime/opponent/harness/orchestration hashes, PGNs, clocks, failures and reports. Record missing evidence explicitly.
4. When all eight runs are terminal, write compact_cycle_01/campaign_closeout_60s_01.json and CAMPAIGN_REJECTION_60S.md with WDL, points, actual wins, planned/finished counts, complete-pair counts, termination/failure counts, stopped reasons, manifest hashes and per-file runtime hashes. Do not fabricate full 50-game reports for stopped screens. This generation is already ineligible for promotion; closeout completion is still pending parent results.

## Phase 2 — choose and freeze one baseline

Use completed direct-parent evidence, common-opening subsets where possible, silky/SF7 performance, reliability, work measurements and attribution/simplicity. A noisy >50% partial result is insufficient. PVS is a useful exact-search reference even if ordered becomes the production base. Keep old and RL weights distinct; do not silently combine the ordered source and RL weights.

Write BASELINE_MANIFEST.json with the actual selected parent, decision evidence and exact runtime/weight hashes only after diagnostics settle. Current manifest deliberately says selection_pending and records eligible source identities. Copy the selected runtime to an isolated Search V2 baseline directory; rehash after copy, record dependencies, coefficient and timing settings, verify legal/clock behavior. No edit to any old playing/frozen directory.

## Phase 3 — measure and test before pruning

ARCHITECTURE_AUDIT.md is the source-grounded feature matrix. Highest priorities are quiescence work, move ordering, absent selective search and expensive conservative TT/key handling. Their relative impact remains a hypothesis.

Implement SEARCH_METRICS.md: a frozen diverse 200+ position suite, isolated instrumentation, disabled-path parity, full metric definitions, deterministic fixed-depth measurements and actual-clock probes. Expand independent checks for EP pins, promotions, checks, terminal ordering, repetition/halfmove contexts, TT bounds/collisions, board restoration and abort behavior. Keep historical losses as regression probes with provenance; do not use future confirmation positions.

## Phase 4 — single-mechanism candidates

1. **Ordering / SEE:** if quiet history is selected in the baseline, do not add it again. Implement our own static exchange calculation, checked against a slow legal capture-exchange oracle on curated and randomized positions. Handle x-rays, pins, king captures, EP and promotions. Start with capture ordering only; SEE pruning is a separate experiment. Compare bad-capture search volume, first-move cutoffs and equal-depth work.
2. **LMR:** revisit the isolated own-code prototype only after broad measurement. Reduce sufficiently late quiet nonchecking moves at safe non-PV nodes, protect promotions/check evasions/important ordered moves, and restore full depth after a reduced fail-high. Check mate windows and shallow depths. Existing four-position work savings are not a gate pass.
3. **Verified null move:** separate variant; guard check, depth, mate window, material and zugzwang-prone endings. Synthetic passes must not contaminate legal repetition history or reuse incompatible TT bounds. Verification search and failure tests are required before a tournament.
4. **Pruning families:** evaluate reverse futility, shallow futility, LMP, history/SEE pruning separately, with tactical/terminal safeguards and measured skip counts. Reject changes that save nodes by losing correctness.
5. **Aspiration / TT / history extensions:** each gets its own lineage and comparison. Measure whether narrower windows, improved TT replacement or richer history improve work and games. Do not bundle changes merely because they are conventional.
6. **Advanced techniques:** IIR, ProbCut, singular/check extensions only after simpler search changes are stable and useful. No simultaneous board rewrite, evaluator tuning or time-allocation tuning.

For every variant: manifest the one delta, correctness checks, fixed-depth suite, low-clock tests, direct-parent 50-game screen; reject clear regressions. Only promising survivors proceed to SF7 first, then silky. Declare continuation criteria before the comparison; a 50-game screen is noisy. Use paired uncertainty and raw results. Do not launch new CPU-heavy tournaments until the existing slots free. Control host load for timing claims.

## Phase 5 — combine and qualify

Combine only independently positive mechanisms, then compare the combination to the same canonical baseline and constituent parent. Interactions can reverse individual gains. A combination must repeat both target screens; parent wins alone do not qualify it.

If a fixed candidate clears both 60s development gates, freeze it and predeclare the independent 120s+0.5s confirmation bank/sample. Require >=70/100 points vs exact silky and >=50/100 actual wins vs SF7, plus zero illegal moves/crashes/time forfeits. Report pair-aware uncertainty without claiming the underlying population rate is proved. If confirmation fails, record rejection; that bank is development evidence thereafter and cannot be reused as unseen confirmation.

## Phase 6 — neural work only when justified

Resume supervised/outcome learning if Search V2 evidence shows evaluation is limiting or after a successful search improvement needs a separately measured value update. Generate diverse own trajectories against a curriculum including higher Stockfish skills; retain weaker/self-play positions to avoid almost-all-loss targets. Separate opening/game groups across train/validation/test, preserve supervised replay, monitor saturation/sign/extreme/queen probes, compare to the frozen parent, export and verify sparse/dense/compiled parity. No borrowed nets. A lower validation loss never triggers promotion by itself.

## Phase 7 — the requested agent.zip

Only after final strength and reliability gates: refresh official rules, run relevant lint/type/unit/legal fuzz and actual-clock checks, verify allowed dependencies and no runtime network/GPU/subprocess/native binaries, check package root and all weight files, verify size, deterministic build and SHA256. Preserve the previous root agent.zip. Extract the new artifact into a clean directory, compare every runtime hash with the qualified snapshot and play platform-style smoke games from the extraction. Deliver the new zip and promotion report. Do not upload.

## Exact immediate next action

The 240-position suite is now frozen and validated; metric definitions are saved but instrumentation/search measurements are pending. Monitor the two parent writers (snapshot07:38 games each). Once both finish, perform closeout, select/freeze baseline, then instrument and run the broad suite. No new training or candidate tournament has been launched by this audit. CONTINUATION_PROMPT.md contains the complete runnable handoff context.
