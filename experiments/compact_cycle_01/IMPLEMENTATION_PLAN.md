AUTHORITATIVE SEARCH V2 REVISION (2026-09-08): Read ../search_v2/IMPLEMENTATION_PLAN.md and ../search_v2/CONTINUATION_PROMPT.md first. They supersede all older current-state/protocol sections below. Six60s target runs are stopped for futility; only two parent diagnostics remain. Pause blind RL; baseline selection pending completed diagnostics. Development60s+0.5s/50games; independent final120s+0.5s/100games pertarget. No qualifying candidate or new ZIP.

AUTHORITATIVE LATEST USER REVISION: local candidate screens now use60seconds+0.5seconds and50games each (25pairedopenings). This supersedes earlier120second/20game screen instructions. All eight prior120second compiled screens were intentionally stopped; their completed records remain historical and MUST NOT be pooled with the60second games. Fresh directories and active session IDs are in campaign_60s_50g.json. Existing120second RL trajectories remain valid training evidence only; future training should match the revised60second local protocol. No qualification or promotedZIP yet.

Current run-state correction: older centered/silky58770 and old-value/silky6570 were STOPPED for mathematical futility at the planned20game >=70% score screen; preserve their records and futility_decision.json, do not resume stale locks. Replaced with ordered/silky25994 and ordered/SF7 35288. Other live handles: PVS/silky27429, PVS/SF7 83478, ordered/parent91270, newRL/parent58536, newRL/silky45604, newRL/SF7 70806. All current runs120000+500,oneworker,screenbank,10pairs,recorded. See CYCLE_STATUS for audit snapshots; no qualification yet.

Newest completed RL cycle: SF7 full-clock64game training finished and audited (4681train/1567val positions;50train/14val games). Guarded CUDA epoch9 selected, outcomeBCE0.8039724->0.7668795, teacherMAE108.9943->107.9818cp. Frozen weight-only compiled_sf7_rl_01 passed checkpoint export and500position compiled parity. Live fullclock20game screens: parent58536, silky45604, SF7 70806. Ordered-search parent screen is also live91270. See newest CYCLE_STATUS for exact paths and conditions; older live snapshots below are superseded.

# Current implementation plan — 120s + 0.5s campaign

Latest checkpoint: compiled_pvs_01 is now frozen and under two full-clock20game screens: vs silky session27429/output compiled_pvs_01_silky_120s; vs SF7 session83478/output compiled_pvs_01_sf7_120s. TT/PVS correctness and agent history/clock tests passed. See latest CYCLE_STATUS section for details. These supersede older statements that the prototype lacks an agent. No promotion achieved; do not edit frozen playing files. Refresh all live handles before action.

Updated 2026-09-08. This current section supersedes the historical record below. Read CYCLE_STATUS.md for the chronological evidence trail; process/session IDs are observations, not proof a process is still running.

## Objective and authorization

Continue local development and outcome reinforcement learning until a frozen candidate earns at least 70% SCORE against the verified silky-snow flagship and at least 50% actual WINS against Stockfish skill 7, then build and verify agent.zip. Score=(W+0.5D)/N; win rate=W/N. These are distinct requirements. No qualifying candidate or new promoted ZIP exists yet. No upload is authorized. Preserve the dirty tree, use no subagents, and never edit harness/ or ship third-party engines/models.

The user corrected the tournament clock: **120000 ms initial time + 500 ms increment per move**. This applies to every new candidate comparison and promotion match. Earlier 10s/0.1s and 30s/0.3s results are development/training evidence only. Future stronger-opponent training also uses the full clock for distribution matching. Do not reinterpret old results as qualifying.

## Verified foundations and completed work

- Repository MilkyWay, recorded main/834ceb8, with substantial pre-existing dirty/untracked work. Repository Python is .venv/Scripts/python.exe; GPU Python is training/.venv/Scripts/python.exe (RTX 2060, torch 2.6 CUDA 12.4). One writer per output directory.
- audit_flagship_archive.py verified experiments/silky_snow runtime matches its agent.zip and root agent_silky_snow.zip, archive SHA256 e191db92ed72053a1fb0ebd06c257c7ce9ab355dd5423d0b9ff9517afbf193ef. Root agent.zip is different and must not be silently substituted.
- Compact supervised residual: 768→16→1, exact mirrored colour antisymmetry, bounded +/-400 cp. Teacher data 61,758 train / 6,718 validation / 3,526 test. CUDA best epoch 15; validation MAE 119.02666→97.12575 cp. Prediction improvement is not playing strength.
- Full-strength residual lost its 20-game short-clock screen: 17.5%, +2=3-15. Fixed-depth work found a large increase in quiescence nodes. Quarter-strength residual scored 57.5% against silky in a small short-clock screen; not a promotion result.
- First 16-game self-play outcome update passed export/parity checks but scored only 45%, +6=6-8, directly against silky at the old short clock. Second 64-game self-play cycle improved teacher loss but worsened outcome validation. Its guarded diagnostic selected epoch -1 (no update), so neither was promoted.
- Team-trained v6 policy had better offline move agreement. Quarter+v6 scored 60% against its parent but only 47.5% against silky in short-clock tests. Centering quiet logits before clipping repaired artificial ties; 256 random-position tests passed legal-set, TT-priority and common-offset invariance. Frozen compact_quarter_policy_v6_centered is under full-clock test.
- Higher-opponent learning is implemented, not merely proposed. Two completed 16-game SF6/SF7 batches at the previous training clock were merged by starting-FEN group to prevent overlapping openings crossing train/validation splits. Dataset compact_sf67_outcomes_01 has 2,600 train / 545 validation positions. Guarded CUDA outcome update selected epoch 9; validation BCE 0.9078056→0.8925008 with effectively unchanged teacher MAE. Export and sparse runtime parity passed. Frozen compact_sf67_value_01 changes only value weights relative to the centered-v6 parent.
- Training is currently Monte Carlo terminal-outcome value learning with supervised replay; do not call it policy-gradient learning. No published net is used. Stockfish supplies offline opponents/labels only.
- Compiled-core prototype implements original array-board move generation, including EP/castling/promotions. Passed five reference perfts, 1,000 random legal-position comparisons and 30,790 make/unmake transitions. Compiled evaluation matches existing classical+learned evaluation exactly on 2,000 random positions. A simple unpruned alpha-beta/quiescence search now exists and passed 12 independent reference-score cases, terminal/repetition checks and 30 deadline checks (20ms requested, maximum 20.452ms after warmup). This prototype is not a packaged agent or proven improvement.

## Active work — inspect before launching anything

1. Full-clock centered policy vs silky: output experiments/compact_quarter_policy_v6_centered_silky_120s, session 58770. Ten pairs, screen bank, one worker, recorded games, 120000+500. Latest observed three pairs / six games / four points; PARTIAL.
2. Full-clock outcome-value challenger vs silky: output experiments/compact_sf67_value_01_silky_120s, session 6570. Same protocol. Latest observed two pairs / four games / zero points; PARTIAL.
3. Higher-opponent training: training/datasets/compact_sf7_fullclock_01, session 40752. 64 games, four workers, seed 20260913, Skill7, 120000+500, compact_sf67_value_01. Latest observed IDs 0–22 saved; refresh manifest/files. These are training trajectories, not qualification games.
4. Prototype verification completed in session 65716; results and source hashes are in experiments/compiled_core_01/search_verification.json. These initial checks are not full playing-agent verification. Evaluation parity was rerun after import-format cleanup.

Do not alter live candidate directories, runners, adapters or their hashed inputs. Query sessions/process command lines before restarting. If a session handle disappears, check the actual PID and parent. Remove a lock only after proving its owning process exited. Never mix a changed protocol or runtime into an existing result directory.

## Next implementation sequence

### A. Complete the running evidence

Read each finished report, raw per-game JSON/PGN, manifest and failure counters. Distinguish colour-specific results from candidate results. Recompute W/D/L, score and actual win rate. Do not pool training games with screens or pool short and full clocks. Keep the current learned model experimental even if its validation loss improved. If it regresses in the completed full-clock screen, retain the better parent and inspect its losses before freezing another challenger.

### B. Complete the faster-search correctness baseline

Keep work isolated in experiments/compiled_core_01. The prototype reuses the team's classical evaluator and current learned residual; it does not port another engine. Verify independent python-chess minimax/quiescence agreement, terminal mate/stalemate precedence, legal EP repetition identity, fifty-move and repetition draws, insufficient material, legal returned moves, board restoration on timeout, and import warmup duration. Explicitly warm every signature before the match clock.

Then add performance mechanisms one at a time: TT with mate-distance normalization and draw-history safeguards, PVS with full-window re-search, stable move ordering, and only evidence-backed selective pruning. Build fixed-depth and fixed-clock probes to distinguish algorithmic node changes from execution speed. Perft throughput alone cannot establish search speed or strength. Preserve the simple reference search for parity on shallow positions. Treat this as a new search variant, not as a value-only ablation.

Before an agent wrapper: reconcile game history from successive FENs, retain only valid same-game history, allocate conservative soft/hard deadlines, retain the last completed legal move, ensure low-clock fallback, and warm all JIT functions within the platform import budget. Use the existing contract and runtime checks. Freeze new runtime hashes before any candidate tournament.

### C. Continue higher-Stockfish reinforcement learning

The current training opening file sf_curriculum_openings_01.json contains 32 positions from distinct source games, early balanced positions assessed offline, excluding existing development/screen/confirmation starts. Audit source IDs and split groups again when combining batches. Never train on final confirmation games or choose training positions from their failures.

After all 64 current games complete: verify PGN legality and terminal results, IDs, no failures, opening-pair split isolation and class diversity using prepare_compact_outcomes.py. Check whether the model selected as training parent is actually suitable; a trajectory generator need not become the next champion. Run a guarded GPU update from the chosen frozen parent with the correct 0.25 runtime coefficient applied once, supervised replay, fixed initial LR 1e-4, and a new output directory. Include epoch -1 so a worse update is rejected honestly. Compare outcome calibration/BCE and teacher loss, not just training loss. Export exact checkpoint, verify dense/sparse parity and mirrored symmetry before freezing.

Use Skill7 regularly, with a mixture of earlier levels and frozen self-play opponents when losses become nearly uniform. Raise training opposition to higher skills only as a documented curriculum experiment; strength of the opponent alone does not ensure useful gradients. Keep colours/openings balanced and retain supervised replay to reduce forgetting. Increase trajectory diversity before repeatedly tuning on a tiny validation set. If terminal rewards are too sparse, test offline teacher-guided targets as a separate declared mechanism, keeping outcome metrics and direct playing tests as the acceptance evidence. Do not claim teacher imitation is policy-gradient RL.

For each selected model: test only the weight change against its frozen parent first, then directly against silky at 120000+500. Reject regressing updates and preserve lineage/provenance. If compiler work changes the search, test it separately before combining a proven search improvement with a selected value update.

### D. Predeclare promotion protocol before final confirmation

Use independent opening pairs and reversed colours. Screen banks have now been observed; they cannot be the final independent confirmation set. Audit/create a separate bank without using candidate outcomes to select it. Recommended fixed final sample: 50 pairs / 100 games per opponent. Record seed, positions, TC, workers, adapter settings, hardware, source/weight/binary hashes and any adjudication. Do not stop early on a favourable score or repeatedly reuse a confirmation set to tune.

Required observed gates: >=70% score versus the exact silky snapshot, >=50% actual wins versus SF7, and no illegal moves/crashes/time forfeits. Report uncertainty using opening-pair-aware estimates and raw W/D/L. A confidence interval is not proof of a population threshold. If stronger statistical assurance is wanted, predeclare additional sample sizes/criteria before examining those samples. Development screens cannot be presented as final confirmation. Skill6 can diagnose readiness but does not replace the skill7 gate.

Stockfish specification: recorded binary hash, Skill7, Threads1, Hash16; unchanged baseline adapter; no STOCKFISH_TIME_PER_MOVE_MS override. Its clock allocation is max(0.05,min(1.0,(time_left_ms/1000)*0.05)), then min(that,max(0.001,time_left_ms/2000)). At a healthy 120s clock the cap is 1 second per move. Record this alongside 120s+0.5s, not an invented Elo/depth estimate. Do not weaken the opponent to pass a gate.

### E. Reliability, promotion and agent.zip

Refresh canonical competition rules/contract before packaging. Run relevant lint/type/unit checks, tactical/legal fuzz and actual-clock reliability probes for the changed runtime. Verify the platform import/warmup budget and single-core CPU behavior, dependencies, package size, no native binaries or Stockfish assets, and no runtime GPU/network/subprocess dependency. Leave harness/ unchanged.

Once both final strength gates and reliability pass: freeze the exact winning runtime, write PROMOTION_REPORT with raw results, intervals, provenance and limitations, package deterministically with agent.py at ZIP root, extract to a clean directory and play from that extracted archive. Check every loaded weight is included. Verify extracted runtime hashes equal the tournament snapshot. Preserve existing archives before installing the final root agent.zip. Return its absolute link, SHA256 and qualifying results. Do not upload. If gates fail, continue a measured next cycle and record the rejection rather than packaging an unqualified candidate as success.

## Continuation discipline

Read this current section and CYCLE_STATUS.md first. The historical text below is retained for provenance and contains obsolete 'not run' labels, partials and clocks. Do not execute its old commands blindly. All newly launched comparisons use explicit --base-ms 120000 --increment-ms 500. Existing data/results remain immutable. Continue authorized local work without another permission question; be precise about completed, live, rejected and untested work.

## Historical implementation record (superseded where noted)

# MilkyWay improvement campaign: implementation plan and continuation handoff

Recorded 2026-09-08. This document supersedes the September 6 Astralix handoff for the current compact-value experiment. Historical reports remain evidence of earlier work, not evidence that the current promotion gates have passed.

Final save-time refresh: the screen advanced to 9 saved pairs / 18 games, with 3.5 points = 19.44% score. Still partial; the 12-game snapshot below documents the earlier process inspection, not the latest score. Read pairs.json again on resume.

## 1. Objective, scope, and present decision

Find a materially stronger engine, compare it directly with the frozen silky-snow flagship, validate it against Stockfish, and produce a new `agent.zip` only after a good candidate passes promotion. The carried-forward campaign targets are at least 70% score against silky-snow and at least 50% wins against Stockfish skill 7. Score means `(wins + 0.5 * draws) / games`; win rate means `wins / games`. These are different tests. Retain the earlier skill-6 diagnostic stage before skill 7.

Status: NOT ACHIEVED. No new candidate has qualified, and no new promoted archive has been produced by the compact-value work. The current model improves held-out prediction error but is losing its development tournament badly. Do not describe it as an upgrade.

The latest user request is for this implementation plan and continuation prompt. This handoff does not launch further training or tournaments. An already-running tournament was left running; refresh its results before continuing. Local candidate development and eventual packaging are authorized by the earlier request. Uploading is not.

## 2. Repository and operational constraints

- Repository: `C:\Users\Babar\Documents\Coding\Projects\chess_bot\MilkyWay`; its parent is not a Git repository.
- HEAD verified as `834ceb8`. Earlier branch state was main; recheck branch on resume.
- Preserve existing modified files: `.gitignore`, `engine.py`, `engine_types.py`, `evaluation.py`, `search.py`, `time_manager.py`, `tests/test_harness_rules.py`, `tests/test_package_determinism.py`, and `training/data/download_pgn.py`.
- Many experiments, datasets, checkpoints, scripts, reports, and archives are untracked or ignored. Do not clean/reset the tree. Existing harness-related dirty tests predate this handoff.
- Read root `AGENTS.md`. Never change `harness/` to make a candidate pass. Never ship Stockfish, third-party engines/networks, or offline labeling assets.
- Use `.venv/Scripts/python.exe` for repository execution; use `training/.venv/Scripts/python.exe` for GPU training. The recorded training runtime is torch 2.6 with CUDA 12.4 on an RTX 2060.
- No subagents; conserve usage through bounded experiments and persistent manifests.
- Before packaging, refresh the live competition contract and rules at the URLs in AGENTS.md. Its cached platform limits are not a substitute for current rules.
- One writer per output directory. Use new directories for changed models or protocols. Inspect PID and ParentProcessId before treating Python processes as duplicates: a launcher and its child are normal.
- Do not remove a writer lock merely because an observation session disappeared. Verify the owner exited first.

## 3. Historical work and how it relates to this campaign

### Classical and Astralix stages

The September 6 handoff records MW-0.2's classical baseline, rejected R34 candidates, upstream synchronization, balanced master-position preparation, offline Stockfish labeling, and several neural-value attempts. It reports 72,002 balanced records and identifies an earlier dataset whose value targets were all +1.0. That degenerate dataset must not be reused as evidence of successful learning.

Astralix v1 combined policy/value integration and timing changes and regressed: its historical SF6 screen scored 8.3%, versus 37.5% for the classical/depth baseline. Those were small historical experiments. The original next step was a controlled policy-only ablation. The repository subsequently advanced to silky-snow and then compact-value work; do not restart old R1 without first reading its saved outputs and deciding what unanswered question it would resolve.

### Silky-snow stage

`experiments/silky_snow` is the frozen comparison directory used by the current tournament. Its runtime uses classical evaluation and the existing policy ONNX model. The previously trained large neural value head was not successfully integrated into the playing engine.

The older promotion report records a 58.8% development score followed by 48.5% over 100 confirmation games against the preceding flagship. Its SF7 result is 17.5% SCORE over 20 games at 10 s + 0.1 s. This is neither 17.5% win rate nor evidence that the present targets passed.

Do not repeat that report's claims that faster search necessarily sits idle rather than searching deeper, that the target is impossible, or that a particular Elo gap follows from these results. Those conclusions are not established. Audit the actual time/depth behavior instead. Also verify the directory hashes against the intended flagship archive before final confirmation; filenames alone do not establish artifact identity.

## 4. Completed compact-value work

### 4.1 Supervised initialization dataset

Implemented `training/scripts/compact_value_cycle.py` with prepare and train modes. Preparation reads the existing `master_value_v2` splits, reconstructs valid nonterminal boards, and saves:

- 768 binary piece-square inputs, using the first 12 representation planes;
- a white-relative classical evaluation anchor from frozen silky-snow;
- a white-relative centipawn target recovered from the existing normalized teacher target.

Prepared dataset: `training/datasets/compact_cycle_01`. Recorded counts are 61,758 train, 6,718 validation, and 3,526 test positions. Source and baseline hashes are in its manifest. Existing split membership was retained; this does not itself prove original game-level independence. Audit original game provenance before calling the test set fully independent.

### 4.2 GPU model training

Output: `training/checkpoints/compact_cycle_01`.

Architecture: 768 inputs, 16 ReLU hidden units, scalar output. Evaluate original and colour/rank-mirrored inputs, subtract their outputs, and apply a tanh-scaled residual bounded by 400 cp. Add that residual to the frozen classical anchor. This enforces colour antisymmetry by construction.

Training used CUDA, seed 20260908, 30 epochs, learning rate 0.001, AdamW, and a normalized Huber objective. Best recorded validation MAE: 97.12575 cp versus classical 119.02666 cp, an approximately 18.4% reduction. The recorded best epoch is 15. Artifacts include `best.pt`, `compact_value.npz`, `history.json`, and `manifest.json`.

This is supervised initialization, not completed reinforcement learning, and lower MAE is not proof of playing strength. The test set has not been used for the reported model-selection metric.

### 4.3 Frozen playing candidate and CPU verification

Candidate: `experiments/compact_cycle_01`.

Copied silky-snow's runtime and policy weights. Added `compact_value.py` and `weights/compact_value.npz`; changed the search evaluation import to the wrapper. The wrapper adds a side-corrected learned residual to classical evaluation. The sparse CPU implementation accumulates occupied piece-square embeddings with a warmed numba kernel.

`tools/check_compact_value.py` produced `verification.json`:

- 500 random legal positions checked;
- maximum dense-export versus sparse-runtime difference 0.0001742 cp;
- mirror antisymmetry and residual-bound assertions passed;
- classical evaluation about 8.275 microseconds; compact evaluation about 13.444 microseconds in this local microbenchmark;
- approximately 62% extra evaluation cost, which may reduce search depth;
- source and weight SHA-256 hashes recorded.

Earlier local smoke observation: import/warmup about 6.8 seconds and a legal move returned. These are local measurements, not platform certification. Direct PyTorch checkpoint-to-export parity, broader reliability tests, and full repository gates remain outstanding. Prior execution recorded Ruff clean for the new scripts; it did not establish a full clean repository gate.

### 4.4 Self-play data generation

Implemented `tools/compact_selfplay.py` using the unchanged referee, separate persistent agent processes for each side, actual clocks, seeded opening variation, explicit game IDs, game-level train/validation assignment, per-game PGNs, source hashes, and an exclusive writer lock. Reliability failures raise instead of silently inserting fallback moves.

All 16 expected records now exist in `training/datasets/compact_selfplay_01`, IDs 0 through 15. No writer lock was present and no matching self-play process was found at handoff inspection. This establishes that the output batch is present; perform a full record/PGN audit before training. Expected split: 12 training games and 4 validation games. Sixteen games are a pipeline smoke batch, not sufficient strength evidence.

Do not reuse the old scratch self-play generator without repair: earlier inspection found shared engine state between colours, clock handling that could hide flags, fallback moves, and inadequate game provenance.

### 4.5 Outcome-learning implementation, not yet executed

`training/scripts/prepare_compact_outcomes.py` reads the saved games, verifies PGN result headers and legal move sequences, computes frozen classical anchors, and writes white-perspective targets: white win 1, draw 0.5, black win 0. It preserves game-level splits and records hashes.

`training/scripts/train_compact_outcomes.py` warm-starts the compact checkpoint on CUDA. It combines supervised replay with a Monte Carlo outcome-value loss: Huber teacher replay plus 0.05 times outcome BCE; learning rate 0.0001; 10 epochs by default. It evaluates the starting checkpoint as epoch -1 and can retain it if later epochs fail to improve the selection objective.

Neither outcome preparation nor outcome training had been run at the verified handoff state. These are implemented scripts, not a completed RL result. This is outcome value learning, not a policy-gradient algorithm. The hand-chosen cp-to-outcome logistic conversion and loss weighting require calibration checks.

## 5. Running tournament: do not duplicate it

Command already launched from the repo:

```powershell
.venv/Scripts/python.exe tools/candidate_screen.py --agent experiments/compact_cycle_01 --opponent experiments/silky_snow --out experiments/compact_cycle_01_screen --pairs 10 --workers 1 --bank dev --base-ms 10000 --increment-ms 100
```

At handoff inspection, launcher PID 29328 and Python child PID 15376 were active, with a candidate runner descendant. PIDs are observational, not durable identifiers; recheck them. Six saved pairs contained 12 games: 1 win, 1 draw, 10 losses, score 1.5/12 = 12.5%. This is a PARTIAL result, not the final 20-game result. All recorded terminations in that snapshot were checkmate or insufficient material.

Read `manifest.json` and `pairs.json` again on resume. Keep both playing directories immutable until the run completes. Do not infer new results from elapsed time, and do not restart an active run. If interrupted, inspect runner resume behavior and manifest matching before resuming the exact command. Preserve complete pairs and distinguish incomplete games from losses.

## 6. Ordered implementation plan

### P0. Recover and freeze the evidence

1. Read AGENTS.md, this handoff, the screen manifest, training manifest, and verification report.
2. Check git status, current processes, output locks, and all final/partial results. Record timestamps and hashes.
3. Audit all 16 self-play records: unique IDs, valid results, legal PGNs, matching starting FENs, terminal conditions, clock records, and no hidden reliability failures. The current converter does not independently enforce every one of these checks; strengthen validation if necessary.
4. Finish collecting the current screen. Produce exact W/D/L, score, failures, and paired uncertainty. Preserve PGNs if the screen tool does not already retain them; do not pretend missing PGNs can be reconstructed from pair summaries.
5. Confirm that frozen silky-snow is the intended previous candidate by comparing source/model hashes with the relevant archive manifest. Resolve any mismatch before a qualifying tournament.

Acceptance: reproducible completed screen and audited self-play batch; no duplicate writers and no promotion claim.

### P1. Diagnose why the compact model loses

Do this before blind scale-up. Check input-plane ordering against training tensors, white versus side-to-move sign, mirror mapping, model export, residual scale, and search score usage. Add direct checkpoint-versus-export-versus-runtime comparisons on fixed positions, including promotions, checks, castling rights, en passant, extreme material imbalance, and endgames.

Run isolated fixed-node/depth and fixed-clock probes. Record nodes, completed depth, elapsed time, principal move, and score. Fixed-work tests assess evaluation decisions; fixed-clock tests include overhead. Stop other compute-heavy work during timing comparisons.

Create new immutable diagnostic variants, not edits to the running snapshot:

- classical control;
- wrapper computing the residual but applying coefficient zero, to isolate overhead;
- the same learned residual at a small predeclared coefficient, to test score disruption;
- full residual as already screened.

Choose a bounded sequence rather than a large tuning grid. Investigate draw/mate handling and pruning assumptions if scores are badly distorted. Do not conflate prediction accuracy, latency, and game strength. If the model remains harmful, reject its integration and keep its evidence.

Acceptance: at least one supported explanation and a corrective variant that improves the failing diagnostic; no unmeasured claim that RL will repair a runtime bug.

### P2. Execute and verify one outcome-learning cycle

After the batch audit, these commands are ready. They refuse to overwrite existing output; inspect existing outputs first when resuming.

```powershell
.venv/Scripts/python.exe training/scripts/prepare_compact_outcomes.py --games training/datasets/compact_selfplay_01 --out training/datasets/compact_outcomes_01
training/.venv/Scripts/python.exe training/scripts/train_compact_outcomes.py --data training/datasets/compact_outcomes_01 --replay training/datasets/compact_cycle_01 --checkpoint training/checkpoints/compact_cycle_01/best.pt --out training/checkpoints/compact_outcomes_01 --epochs 10
```

Before trusting the run, validate finite inputs/targets, split separation, colour/result distribution, baseline loss, and target perspective. Log GPU device, seeds, parent/data/trainer hashes, loss curves, chosen epoch, and checkpoint/export hashes. Check whether the best checkpoint is still epoch -1; if so, report no selected update rather than claiming successful reinforcement improvement.

Avoid letting very long games dominate outcome learning without examination. Consider per-game weighting or capped position sampling in a separate documented experiment. Diagnose the outcome conversion and replay weighting using validation rather than tuning on the final arena.

Freeze any selected new model into a new candidate directory with identical runtime where possible. Repeat parity, antisymmetry, boundedness, legal-move, and latency checks. Compare against both its supervised parent and silky-snow on paired development positions.

Acceptance: a traceable actual outcome-learning run and honest game results. Improved loss alone does not advance promotion.

### P3. Iterate efficiently, one mechanism per experiment

If diagnostics support the model, increase self-play diversity and quantity in stages, for example 64 then 256 games, only after the small pipeline passes. Use new game IDs/seeds and frozen parent checkpoints. Preserve entire games in one split and audit duplicates across teacher, self-play, and evaluation sets.

Keep a champion/challenger ledger: parent hashes, sole intended change, data provenance, training selection metric, runtime cost, arena results, and accept/reject reason. A failed challenger must not silently become the new parent.

If overhead dominates, test smaller hidden widths or a simpler residual architecture as separate candidates. If score calibration dominates, test a limited residual coefficient or calibrated targets. If search has a verified defect, fix and test it separately before combining with learned evaluation. Do not simultaneously tune evaluation, neural integration, pruning, and time management.

Use small development screens for rejection; require independent confirmation for advancement. Repeatedly selecting the best result on the same bank creates selection bias. Create and freeze a fresh confirmation set with recorded provenance; do not assume an old bank is untouched. Do not promise a particular number of cycles will reach the goal.

### P4. Predeclare the qualifying tournament protocol

Before the final candidate is selected, write a protocol with exact artifact hashes, bank and seed, paired colours, games, clocks, failure accounting, and uncertainty method. Recommended confirmation size is at least 100 games per opponent, but this is a proposed evidence standard, not a previously completed test. Avoid repeatedly peeking and extending until a threshold is crossed.

Silky-snow gate: at least 70% score under the declared conditions. Stockfish skill-7 gate: at least 50% actual wins under the declared conditions. Report W/D/L and both metrics for each. Use pair-aware intervals for score and disclose correlation/uncertainty for wins. A point estimate meeting a threshold does not prove true strength is above it; if confidence-bound acceptance is required, predeclare that stronger rule explicitly.

Retain 10 s + 0.1 s only for development comparisons. The earlier SF campaign specification was 30 s + 0.3 s, one worker, paired colours, seed 20260906; pin that for the campaign instead of quietly substituting an easier clock. Confirm separately at the current platform clock after fetching the live rules. Do not pool different clocks into a single headline result.

Stockfish specification: verify the actual binary path and SHA-256 per run, Skill Level 6 for diagnostics then 7, Threads 1, Hash 16, and no accidental fixed-movetime override. Earlier manifests may use AVX2 despite chat calling it universal; the recorded binary hash is authoritative.

The adapter currently computes seconds as:

```python
time_limit_s = max(0.05, min(1.0, (time_left_ms / 1000.0) * 0.05))
time_limit_s = min(time_limit_s, max(0.001, time_left_ms / 2000.0))
```

At 30,000 ms and 120,000 ms the result is 1 second. The old 15 ms figure is wrong. Do not attach unsupported depth/NPS estimates or Elo mappings to skill levels. Verify actual UCI setup succeeds rather than relying only on requested values in a manifest.

Read `tools/benchmark_stockfish.py --help` before composing its command; no unverified flag syntax is prescribed here. Inspect resume/manifests before extending any existing output directory. Keep the referee unchanged, record failures, and retain raw game evidence.

### P5. Reliability and promotion

For a qualifying frozen candidate, run focused correctness checks, appropriate repository tests, Ruff/mypy with existing failures distinguished from regressions, low-clock probes, repeated-process/game-state checks, legal-move fuzzing, and import/model warmup tests. Validate the runtime under the current documented platform constraints. A clean local run is not a claim of full platform equivalence.

Write `REPORT.md` with exact opponent/candidate hashes, training lineage, tournament conditions, W/D/L, score, win rate, intervals, failures, and limitations. Include direct results against silky-snow, not just against an older baseline or the weak compact parent. If either gate fails, record rejection and return to diagnosis; do not package the failed candidate as the new flagship.

### P6. Build the final agent.zip

Inspect the existing packager and supported arguments before use. Package the frozen winner explicitly; do not accidentally package the dirty root tree. Use an allowlist containing runtime Python and actually loaded weights, with `agent.py` at archive root. Exclude Stockfish, labeling/training data, checkpoints not loaded at runtime, logs, caches, and unrelated experiments.

Build to a candidate-specific path first. Check deterministic contents/hashes and current size/runtime constraints. Extract to a clean directory and run smoke games from that extraction so missing imports or weights cannot be supplied accidentally by the repository. Verify extracted source/model hashes match the tested candidate; exercise substantive regression games from the archive when practical.

Only after promotion and archive verification, create the requested final `agent.zip`, preserving the previous artifact. Write its SHA-256, contents manifest, and promotion report beside it. Return clickable links plus tournament results. Do not upload without explicit authorization.

## 7. Immediate continuation priorities

1. Refresh the running screen; its last verified snapshot was 12 games, not a final result.
2. Audit the complete 16-game self-play batch.
3. Diagnose the compact candidate's regression, especially evaluation overhead versus score disruption.
4. Execute the already-written outcome preparation/training only after those checks; keep new outputs separate.
5. Test a frozen corrected/RL challenger against its parent and silky-snow.
6. Advance only genuinely stronger candidates to independent SF and flagship gates, then package.

No extra confirmation is needed for these authorized local development steps. Missing evidence is a reason to measure, not to claim completion.
