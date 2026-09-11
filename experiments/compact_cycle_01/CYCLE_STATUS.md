# Compact-value campaign status — 2026-09-08

This status supersedes partial results and unexecuted-step labels in the handoff.

## Completed

- Full-residual supervised candidate screen finished: 20 games, +2 =3 -15, **17.5% score**, paired bootstrap interval 5.0–32.5%, no reported failed terminations. Rejected. Evidence: `../compact_cycle_01_screen/report_20.json`.
- All 16 self-play PGNs audited by the strengthened converter for legal moves, starting FEN, result header and actual final-board termination. 11 checkmates, 3 repetitions, 1 fifty-move draw, 1 insufficient-material draw. No failed terminations in the accepted batch.
- Prepared `training/datasets/compact_outcomes_01`: 1,073 training positions from 12 games, 420 validation positions from 4 games. Small diagnostic batch only.
- Ran CUDA Monte Carlo outcome learning with supervised replay for 10 epochs. Output `training/checkpoints/compact_outcomes_01`; selected epoch 0 rather than the unmodified epoch -1. Validation outcome BCE 0.482819 -> 0.474152; teacher MAE 97.125748 -> 96.774788 cp. Later epochs did not improve the combined selection metric. This is real completed outcome training, not a playing-strength claim.
- Direct checkpoint/export parity passed on all 420 validation positions: maximum 0.00009871 cp. Sparse runtime parity passed on 500 random legal positions: maximum 0.00014946 cp. See respective export_verification.json and candidate verification.json.
- Fixed-depth search probe completed on ten development positions, comparing classical, compute-only residual coefficient zero, 0.25, and 1.0. Zero coefficient preserves all tested moves, scores and node counts. Full residual changes moves and can greatly expand search: bank_016 qnodes 13,783 -> 47,102 at depth 4; elapsed 0.558 -> 2.030 seconds locally. Evidence: `search_probe.json`. This supports investigating score-induced search expansion as well as raw inference cost; it does not prove the sole cause of tournament regression.
- Fixed candidate_screen weight hashing to include all weight files, including NPZ. The original full-residual run manifest omitted NPZ, although its separate pre-run verification.json recorded the NPZ hash. Do not rewrite the historical manifest as if it had included that evidence originally.
- Ruff passed for the newly added/modified pipeline and probe scripts. Full repository gates remain pending.

## Frozen variants and active experiments

`experiments/compact_cycle_01_quarter` uses the original supervised model with coefficient 0.25; only coefficient differs from the rejected full-residual parent.

`experiments/compact_outcomes_01_quarter` uses the selected outcome-updated model at the same 0.25 coefficient. Only weights differ from the supervised quarter variant. Each contains candidate_manifest.json with actual runtime/weight hashes. No promotion or final agent.zip has been made.

Two development tournaments were launched, each 10 pairs, workers=1, dev bank, 10 s + 0.1 s, default seed 20260906:

1. Supervised quarter vs silky-snow: output `experiments/compact_cycle_01_quarter_screen`, execution session 92590.
2. Outcome quarter vs supervised quarter: output `experiments/compact_outcomes_01_quarter_parent_screen`, execution session 95332.

Recheck live handles/processes before resuming. Do not launch duplicate writers or modify frozen runtime files during games. These are developmental, not qualifying confirmations. Both run concurrently, so do not compare absolute performance timings against idle-machine microbenchmarks.

## Next decisions

Collect both complete reports. If the quarter coefficient still regresses, investigate calibration/architecture rather than promote it or blindly generate a large new batch. If the outcome quarter beats its parent, that is still insufficient: it must independently beat silky-snow, then pass the full campaign gates. If the initial outcome update is neutral, preserve that result and expand data only with a specific hypothesis.

Before future promotion runs, add raw PGN retention to the experiment orchestration: the old play_single_pair helper currently discards PGNs. Do not change harness/. Current screens therefore support W/D/L and termination analysis but do not preserve full game trajectories. Also audit the intended silky-snow archive identity and create a genuinely independent confirmation bank.

Goal remains unmet: >=70% score vs silky-snow, >=50% actual wins vs SF7 under pinned conditions, promotion results, and a verified new agent.zip.

## Follow-up: archive audit and interrupted-run recovery

The frozen silky-snow runtime exactly matches both experiments/silky_snow/agent.zip and agent_silky_snow.zip (archive SHA-256 e191db92ed72053a1fb0ebd06c257c7ce9ab355dd5423d0b9ff9517afbf193ef). Root agent.zip is different: search.py and move_ordering.py differ and it includes an extra v6 model. Do not substitute root agent.zip for the opponent. Evidence: flagship_archive_audit.json.

Added tools/recorded_pair.py for future runs to preserve per-game referee PGNs, resume saved games under a caller-owned manifest/lock, and reject void/failure results. Two focused scoring/resume/failure-preservation unit tests passed after a sandbox temporary-directory permission failure was resolved by an approved rerun. This helper is not yet integrated into the running screens.

Both original tournament session handles disappeared. An authoritative process-list check returned no matching live processes and no final reports existed. Resumed both exact original commands with unchanged manifests; completed pairs are reused. New execution sessions: 34760 (quarter vs silky) and 41373 (outcome vs quarter).

Latest partial snapshot: 7 pairs each. Quarter vs silky has 8.0/14 points (57.14%); outcome vs quarter has 8.5/14 (60.71%). Neither is a final or qualifying result. Continue polling these sessions; do not duplicate them.

## Completed screens and second learning cycle

Sessions 34760 and 41373 both completed successfully. Final results:

- Supervised quarter vs silky: 57.5%, +9 =5 -6, paired interval 42.5–72.5%, no failed terminations.
- Outcome quarter vs supervised quarter: 52.5%, +7 =7 -6, paired interval 37.5–65.0%, no failed terminations. Outcome-learning strength gain is inconclusive.

New recorded direct screen is running in session 81857: outcome quarter vs silky-snow, 10 pairs, workers 1, dev bank, 10s+0.1s, output experiments/compact_outcomes_01_quarter_silky_screen. candidate_screen now supports --record-games, preserves PGNs via recorded_pair, records orchestration hashes, and creates an exclusive writer.lock. Existing unrecorded manifests remain compatible with their original mode. Do not modify this runner until the recorded run finishes, because its hash is part of the manifest.

New 64-game self-play batch is running in session 52813: tools/compact_selfplay.py --agent experiments/compact_cycle_01_quarter --out training/datasets/compact_selfplay_02 --games 64 --workers 2 --seed 20260909. This is generated from the supervised quarter parent; the statistically inconclusive outcome challenger has not been promoted into the parent lineage.

The next outcome trainer now accepts --coefficient, so its loss uses the score actually applied by the playing engine. First cycle trained coefficient 1.0 and was subsequently deployed at 0.25. For the second cycle, after the completed PGN audit, prepare compact_outcomes_02 and train from training/checkpoints/compact_cycle_01/best.pt into training/checkpoints/compact_outcomes_02 with --coefficient 0.25 and the same supervised replay. Keep exported raw model coefficients unchanged; the frozen runtime applies 0.25 exactly once. Ruff passed. No second-cycle training has run yet.

## Recorded-loss diagnosis

Added tools/analyze_recorded_game.py to review saved PGNs using offline full-strength Stockfish. This does not change the SF7 opponent or runtime. First reviewed loss: bank_120_black.json in the direct silky screen. A 500,000-node follow-up on plies 53 and 59 confirms large estimated errors: Re8 instead of Rb8 (222 cp), and cxd5 instead of Rxa2 (560 cp). See bank_120_black_deep.json, which records binary hash and analysis conditions.

At ply 59 the candidate had 5.452 seconds and spent about 79 ms (remaining clock 5.473 after the 100 ms increment). The below-six-seconds emergency depth cap warrants investigation. However, a controlled depth-6 probe still chose cxd5 with classical and every tested residual coefficient, so simply removing the cap has NOT been shown to solve this error. No cap-change candidate was built. Evidence: clock_probe_positions.json and clock_probe_depth6.json.

The initial 50k-node review includes a misleading late-game row where unrestricted and forced searches selected the same move but had very different bounded scores. Do not use that raw row as a move-loss claim or aggregate it into ACPL. The analysis tool was corrected to assign zero move loss when its best move equals the played move; the subsequent deep two-position review uses that correction. These bounded oracle estimates are diagnostics, not exact ground truth.

## Direct outcome result and independent policy probe

Direct outcome-quarter vs silky screen finished in session 81857: **45.0%, +6 =6 -8**, paired interval 27.5–62.5%, no failures. All 20 raw game JSON/PGNs retained. The first RL challenger does not qualify and is not the next training parent.

tools/probe_emergency_depth.py tested the recorded ply-59 mistake using identical actual time budgets and preserving emergency search behavior except the iteration cap. Normal: depth 4, 94 ms, cxd5. Uncapped: depth 6, 797 ms, same cxd5. No supported corrective candidate from this probe.

While the second self-play batch runs, audited three existing team-trained root policies on the same 512 reused validation positions. Shipped top-1/top-5: 13.28%/38.09%; Astralix R1: 19.14%/47.85%; v6: 21.88%/57.03%. These are unmasked played-move agreement metrics, not strength/holdout claims. Evidence: policy_audit.json. Historical Astralix R1 itself scored 60% in 20 games against its old no-policy control, but later old-base confirmation was 49% over 100 games; do not present it as a proven upgrade.

Frozen experiments/compact_quarter_policy_v6: identical to supervised quarter except the team-trained v6 policy weights, stored under the existing runtime policy filename. Ten-position depth-4 probe completed; no runtime errors. This model is being tested separately from outcome updates.

New recorded tournament session 66917: compact_quarter_policy_v6 vs compact_cycle_01_quarter, output experiments/compact_quarter_policy_v6_parent_screen, 10 pairs, dev bank, workers 1, 10s+0.1s. Frozen runtime and orchestration hashes recorded. Do not modify its runtime/runner while active.

Self-play session 52813 remains live; latest verified count 34/64. Wait for completion before compact_outcomes_02 preparation/training; do not train on a silently shortened batch.

## Efficiency authorization and completed second GPU cycle

User explicitly requested any legal means, optimized for speed, efficiency and accuracy. Current competition rules/contract fetched successfully on 2026-09-08 and saved as rules_20260908.md and contract_20260908.md. Own models, unrestricted offline engine-labelled training data, books/tablebases, and numba compilation are allowed. Third-party engines/networks remain prohibited in the submission. No upload authorization was added.

Machine verified: 8 physical cores / 16 logical, about 30% CPU at inspection. Stopped only the identified two-worker self-play tree (launcher 27932, writer 41872), verified writer exit, removed its matching stale lock, and resumed exact immutable data/seed/model with six workers in session 20506. Completed all 64 games. This operational change affects training throughput only, not qualification conditions.

Converted and audited compact_outcomes_02: 5,852 train / 1,360 validation positions; 56 checkmates and 8 repetition draws, game-split provenance recorded. Ran GPU training from the supervised parent with actual runtime coefficient 0.25. Run compact_outcomes_02 selected epoch 9 on combined loss: teacher MAE 108.9727 -> 104.4982 cp, but outcome validation BCE worsened 0.522411 -> 0.533300. This is NOT outcome-learning improvement; no candidate was frozen from it.

Ran one bounded loss-weight diagnostic, compact_outcomes_02_balanced: outcome weight 0.5 rather than 0.05, with guard_outcome requiring non-worsening held-out BCE. Every updated epoch regressed; selected checkpoint remains epoch -1. Do not call this an improved or new model. Stop weight-grid tuning on this validation set. Both CUDA runs finished, and no training process remains from them.

Policy-v6 vs parent remains in session 66917; last verified 8 pairs, 11/16 points (68.75%), partial. Direct policy-v6 vs silky screen launched in session 62289, output experiments/compact_quarter_policy_v6_silky_screen, same 10-pair dev/10s+0.1s/one-worker/recorded protocol. Last observed 2 pairs, 1/4 points; refresh before interpretation. No new qualifying result or ZIP.

## User's time-control correction and stronger-opponent training

AUTHORITATIVE USER CORRECTION: tournament games are **120 seconds + 0.5 seconds**. All subsequent candidate comparisons and qualification games must use --base-ms 120000 --increment-ms 500. This supersedes the earlier proposed 30s campaign protocol. Short-clock historical screens are developmental only and cannot establish either promotion target.

Policy v6 final results: 60% (+10 =4 -6) against quarter parent; 47.5% (+8 =3 -9) directly against silky, both 20-game short-clock screens and neither qualifying.

Found clipping-induced policy ties: shipped policy 185/255 validation positions tied at the top after absolute clipping; v6 45/255. Built compact_quarter_policy_v6_centered, changing only quiet-logit centering before clipping. 256 random-position checks passed for common-offset invariance, TT priority and legal move-set preservation. Manifest refreshed after the edit. The short-clock centered-parent screen was explicitly stopped (launcher 17336, child 38212); preserve partial files and its stale lock as abandoned evidence, do not resume it as a qualifying run.

Correct-clock direct comparison now running: session 58770, candidate compact_quarter_policy_v6_centered vs experiments/silky_snow, output experiments/compact_quarter_policy_v6_centered_silky_120s, 10 paired openings, screen bank, workers 1, 120000+500, full game records. This is a full-clock screen, not independent final confirmation. Frozen candidate/runner hashes recorded.

User additionally requested reinforcement learning against higher Stockfish levels when useful. Implemented optional --stockfish-level in compact_selfplay.py, with verified UCI configuration, binary/adapter hashes, alternating candidate colours on identical openings, and opening-pair split membership. Launched two training-only batches BEFORE the clock correction: 16 games each at 30000+300, three workers each, against skills 6 and 7. These may be used as training trajectories, never as qualification evidence. Future opponent training should also match 120000+500.

Active training sessions: 8585 -> training/datasets/compact_vs_sf6_01 (seed 20260910); 46955 -> compact_vs_sf7_01 (seed 20260911). Candidate is frozen unpromoted compact_quarter_policy_v6. Last inspection each had 15/16 games. Stockfish Threads1/Hash16, no fixed-movetime override. Next: finish and audit, then train from these stronger-opponent outcomes.

IMPORTANT BEFORE COMBINING: adjacent seed streams overlap starting positions across the two skill batches. Original per-batch split assignments can disagree for a shared opening. Merge by starting FEN and assign every game from the same opening to one split, with globally unique source/game IDs; never concatenate the two split NPZs blindly. Keep final tournament data out of training. Current SF trajectory batches are not independent holdout evidence.

## Completed stronger-opponent learning update

Both 16-game SF training jobs (8585, 46955) finished normally. tools/merge_opponent_training.py merged them into compact_vs_sf67_grouped_01 by starting-FEN groups, with globally unique game IDs and source hashes. Nine distinct starting openings; 26 training games and 6 validation games. Converter passed all PGN/terminal checks; compact_sf67_outcomes_01 contains 2,600 train and 545 validation positions. These were 30s+0.3s training trajectories initiated before the user's correction, NOT qualifying tournaments.

CUDA run training/checkpoints/compact_sf67_outcomes_01 finished: original supervised checkpoint parent, coefficient 0.25, outcome weight 0.5, guard_outcome enabled, ten epochs. Selected epoch 9. Validation outcome BCE 0.9078056 -> 0.8925008; teacher MAE 108.9727 -> 108.9943 cp, essentially unchanged. This supports an experimental challenger, not a strength claim. Export parity on 545 positions max 0.0001431 cp; CPU sparse parity on 500 positions max 0.0002436 cp; symmetry/bounds checks passed. Ruff passed on changed tools.

Frozen new candidate experiments/compact_sf67_value_01: source/policy identical to compact_quarter_policy_v6_centered; only compact value weights updated from stronger-opponent outcome training. Manifest and verification.json saved. freeze_compact_candidate now supports parents whose residual is already scaled, avoiding double application of the 0.25 coefficient.

Full-clock direct test against silky started: session 6570, output experiments/compact_sf67_value_01_silky_120s, 10 paired screen-bank openings, workers 1, 120000+500, recorded games. The matching unupdated centered-parent vs silky full-clock screen is still live in session 58770. These shared conditions allow comparison without pooling old short-clock results. Neither full-clock run is complete yet. Keep both runtime and orchestration sources immutable while live.

Next: collect both full-clock reports; continue higher-Stockfish learning with future training also at 120000+500. Do not reuse final confirmation positions for training. No candidate has yet met >=70% score vs silky and >=50% wins vs SF7; no new promoted agent.zip exists.

## Full-clock curriculum and compiled-core prototype

Prepared training/datasets/sf_curriculum_openings_01.json: 32 positions from distinct games in master_value_v1/train.jsonl, plies 8–20, filtered to within 80 cp by offline full-strength Stockfish at 50k nodes. All existing screen/confirmation/development bank starting positions were excluded by normalized FEN. Sources, teacher binary, seed and selected positions recorded. This is training data only, not an independent test bank.

Running session 40752: compact_selfplay.py --agent experiments/compact_sf67_value_01 --out training/datasets/compact_sf7_fullclock_01 --games 64 --workers 4 --seed 20260913 --stockfish-level 7 --base-ms 120000 --increment-ms 500 --openings training/datasets/sf_curriculum_openings_01.json. Paired colours, opening-level split, actual SF7 configuration checked. Latest verified 7/64 games, including candidate wins, draws and losses. Do not alter generator/runtime while live; hashes are in its manifest. Once complete, audit/convert and train another guarded outcome update without importing final tournament data.

Full-clock comparisons remain live: parent centered vs silky session 58770 (first completed pair 0.5/2); SF-trained value challenger vs silky session 6570 (no completed pair at last inspection). Both 120000+500, one worker, recorded screen-bank games. No qualifying conclusion from these partials.

New bounded performance work: experiments/compiled_core_01/core.py implements original team-written numba array-board attack detection, pseudo/legal move generation, reversible moves, castling, en passant and promotions. It does NOT contain a searcher or agent entry point yet and is not a submission candidate. No third-party engine source was used.

experiments/compiled_core_01/verify.py passed five reference perft cases (including start depth4=197281 and tactical/castling depth3=97862), 1000 random legal-position move-set comparisons with python-chess, and 30790 make/unmake transitions with exact piece/rights/EP state parity. verification.json records current source hash. Ruff passed. Perft timings measure move generation only, not actual chess search throughput or strength.

Next compiled-core task, if pursuing throughput alongside pending training: add a compiled search around this verified board core. Reuse the team's existing fast_eval._eval_kernel/parameter vector to avoid an unrelated evaluation rewrite, optionally apply the already-trained compact residual, and implement TT/PVS/quiescence plus robust deadline unwinding and repetition/fifty-move/mate handling. Verify evaluation parity, tactical/terminal correctness, import budget, legal moves and clock safety before freezing a candidate or claiming speed/strength. Keep all current playing snapshots untouched.


## Compiled evaluation/search correctness checkpoint

Compiled evaluator reuses first-party classical kernel arithmetic and current trained residual. Only the prototype copy of fast_eval changed its explicit Numba signature to inferred typing to accept readonly global parameter arrays; live candidates remain untouched. verify_eval passed exact integer parity for classical and quarter residual on2000positions.

Added original compiled_search.py: baseline full-legal alpha-beta/quiescence, iterative deepening, legal fallback, deadline polling/unwind, EP-aware position identity, repetition/fifty-move and insufficient-material handling. No TT/PVS/selective pruning or persistent agent wrapper yet. verify_search.py completed:12independent python-chess reference-score positions, mate/stalemate/fifty-move precedence, legal/pinned EP keys, repetition,30legal returned moves and20ms deadline checks. Max elapsed20.452ms after12.212s search warmup. search_verification.json records source hashes. These are initial correctness checks, not strength or deployment proof.

Refreshed IMPLEMENTATION_PLAN current section and CONTINUATION_PROMPT to incorporate120s+0.5s, completed RL cycles, live jobs, compiled prototype and remaining confirmation/package requirements. Older implementation text retained as historical. Last observed matches: centered parent3pairs4/6points; outcome challenger2pairs0/4points; training23/64complete. All partial. No promotion/newZIP.


## Frozen compiled PVS candidate and full-clock screens

Previous goal turn made verified progress (compiled evaluation/reference search and handoff refresh). Current turn added isolated tt_search.py and pvs_search.py; both passed12fixed-depth reference-score comparisons, mate normalization and incompatible-history rejection tests, repeated exact-hit checks and clock/legal probes. TT score reuse requires matching reversible-history multiset, halfmove count, ply and depth; position-only matches may order moves. Baseline30919nodes across probes, TT27507, PVS29362; small diagnostic set, not a strength claim.

Added experimental agent interface with legal opponent-move reconstruction to extend FEN history, reset on unmatched position, soft/hard clock allocation and import warmup. verify_agent.py passed80moves at250ms remaining, max51.522ms, exact history extension/reset, legal1ms fallback. Import20.555s. One120s-clock probe reached depth7,1010409nodes,3.968s search. This is timing evidence, not a tournament result.

Frozen experiments/compiled_pvs_01, runtime165570bytes and hashes in manifest. Includes original compiled core/PVS search, same classical+quarter compact_sf67_value_01 evaluation. No root policy in this new search. Treat it as a whole-search variant, not value-only attribution. Live candidate files remain immutable.

Launched session27429: candidate_screen.py --agent experiments/compiled_pvs_01 --opponent experiments/silky_snow --out experiments/compiled_pvs_01_silky_120s --pairs10 --workers1 --bank screen --base-ms120000 --increment-ms500 --record-games (flags separated normally in actual command). Also launched matching compiled_pvs_01_sf7_120s vs baselines/stockfish --stockfish-level7; session recorded in tool output. Both20game screens, not independent final confirmation.

Older live jobs remain:58770centeredparent vs silky latest4pairs4/8points;6570outcomechallenger vs silky latest3pairs1.5/6points;40752SF7training latest38files including37/38 before36 completed. Refresh actual state, do not assume contiguous IDs or completion. No qualifying results, no promoted ZIP.

SF7 compiled screen session ID:83478. Both new handles verified live after launch.


## Opening provenance and ordered-search experiment

Previous goal turn was progress: TT/PVS implementation, verification, frozen candidate and live full-clock screens. This turn audited all non-test training/datasets JSONL:35947sourcegames724337positions, all records have source_game_id. No exact piece/turn/castling overlap with existing screen/confirm starts; old dev bank overlaps labels/processed training. Test source-game candidates absent from scanned data exist (v2:191games3221positions;v4:1201games24918positions), but NPZ-only data and past tournament provenance remain unaudited. See promotion_openings_audit.json/tools/audit_promotion_openings.py. This is not yet a certified independent final bank.

Added ordered_search.py with quiet killer/history ordering only, preserving full legal PVS/TT/evaluation/timing. verify_ordering.py passed16depth4 score comparisons and deadline/legal probes. Nodes311625->251875 (~19.2% reduction); elapsed1.493->1.301s on small loaded-host probe, not strength evidence. Agent interface passed80low-clock moves/history/reset; max250ms-clock move52.475ms, import24.324s; fullclock probe completeddepth7 before aborting deeper iteration at6.501s.

Frozen experiments/compiled_ordered_01 with runtime/verification hashes, queued for full-clock parent comparison when compute frees. No tournament launched for it yet. Runtime uses same quarter SF-trained compact value, only search ordering changes relative to compiled_pvs_01.

Verification archival correction: prototype agent_verification.json was overwritten by the ordered-agent verification. Original PVS runtime never changed. Preserved still-matching earlier reports under compiled_pvs_01/verification, then independently reran interface checks against the frozen PVS directory into verification/agent_reverification.json; all runtime Python hashes match its original manifest. Fresh checks passed80moves, import27.715s, max53.342ms lowclock, depth7/fullclock6.419s. verify_agent now requires a new explicit --out and supports --runtime to prevent report overwrites. Variations in timings under concurrent work are not speed claims. Run final confirmation under controlled load, without concurrent training/compilation.

Latest verified live: compiledPVS SF7 session83478 firstpair2draws=50%score0%wins; compiledPVS silky27429 stilllive no completepair observed. Training40752 has53games IDs0–52. Older centered/silky58770 last5pairs5/10points; value/silky6570 last4pairs2.5/8points. All partial; no qualification/ZIP.


## Completed full-clock SF7 reinforcement-learning cycle

Session40752 ended normally after all64games. PGN/terminal audit and conversion succeeded: compact_sf7_fullclock_outcomes_01 has4681train/1567val positions,50train/14val games with opening pairs isolated. Training trajectories:13candidatewins19draws32losses;45checkmates18threefold1fiftymove. These are training data, not qualification evidence.

GPU session29506 completed10epochs from compact_sf67_outcomes_01/best.pt with coefficient0.25, outcomeweight0.5, guard_outcome, supervised replay, seed20260919. Selectedepoch9. ValidationBCE0.8039724231->0.7668794990, teacherMAE108.9943085->107.9817657cp. Artifacts training/checkpoints/compact_sf7_fullclock_outcomes_01. Export1024positions max0.0001831055cp;500random dense/sparse max0.0002416127cp, exact compiled evaluation parity, symmetry/bounds passed.

Added tools/freeze_compiled_value.py: schema/finite checks, frozen source copy with only compact_value.npz changed, asserts exact changed-file list and records base/new hashes. Added tools/check_compiled_value.py to verify compiled candidates without importing a root-policy network. Ruff passed. Frozen experiments/compiled_sf7_rl_01 is weight-only relative to compiled_pvs_01 (not the independently modified ordered search). No source/coefficient/time change.

Launched three120000+500,10pairs,screenbank,oneworker,recorded games for compiled_sf7_rl_01:
- parent compiled_pvs_01: session58536, experiments/compiled_sf7_rl_01_parent_120s;
- silky_snow: session45604, experiments/compiled_sf7_rl_01_silky_120s;
- baselineStockfish Skill7: session70806, experiments/compiled_sf7_rl_01_sf7_120s.

Also launched ordered_search parent comparison once training workers began to finish: session91270, experiments/compiled_ordered_01_parent_120s, same full-clock protocol versus compiled_pvs_01. These are diagnostic screens, not final independent confirmations. Eight one-worker screens are now active including the four older ones; do not launch further CPU tournaments until a slot frees. Keep runtime/runners immutable. Final qualification must use controlled load without concurrent training/compilation and report hardware conditions.

Last old results observed: centered/silky6pairs6.5/12points; oldvalue/silky5pairs3.5/10points; compiledPVS/silky1pair1/2points; compiledPVS/SF7two pairs +1=2-1 (50%score,25%wins). All partial. New RL/ordered screens just launched. Neither final target proven; no promotedZIP.


## Screen audit and mathematical-futility stops

Previous goal turn made progress: completed64SF7games, audited, GPUtrained, verified and froze weight-only challenger with three live screens. Current turn added tools/audit_recorded_screen.py: validates frozen agent/opponent hashes, harness/orchestration hashes, legal PGNs, result/terminal consistency, paired colour identity and per-move clock arithmetic. Snapshots recorded_screen_audit_01/02/03.json passed;03includes harness/orchestration checks and auditor hash. These snapshot reports do not prove final strength or completion.

Stopped older candidates only after their observed points made70% impossible within the already-planned20games: centered-v6 parent14games7.5points, maximum13.5/20; oldSF67value12games4points, maximum12/20. futility_decision.json saved inside each run. Verified launcher/child identities before stopping ONLY their descendant process trees (roots19020/8948, writers37244/6676); observation sessions58770/6570 ended with intentional exit1 and process inspection confirmed no owners remain. This is a partial-screen rejection, not a fabricated20game final result or claim about population strength. Preserve stale locks/partials and do not resume these stopped jobs. No runtime or harness file changed.

Used freed capacity for ordered candidate target screens: session25994 experiments/compiled_ordered_01_silky_120s vs silky;session35288 experiments/compiled_ordered_01_sf7_120s vs baselineSkill7. Both10pairs,screen,oneworker,120000+500,record-games. Combined with six remaining jobs, eightoneworker screens are live; no additional CPU tournament until capacity frees.

Latest complete-pair observations: compiledPVS/silky27429:2/6points; compiledPVS/SF7 83478:+3=3-4 over10games (45%score30%wins); ordered/parent91270:+2=2-0 over4games (75%score); newRL/parent58536:+1=0-1 over2games; newRL/SF7 70806:+1=1-0 over2games. RL/silky45604 had one recorded draw at lastaudit but no completepair; newlystarted orderedtarget screens25994/35288 no pair yet. Every number is partial. No candidate meets final qualification evidence; no promotedZIP.

Next: allow current matched screens to resolve, reject mathematically futile target screens honestly if appropriate, inspect losing games before the next mechanism/learning cycle. Do not combine orderedsearch and newRLweights based only on the favourable opening pair. Preserve final independent confirmation bank and controlled-load requirements.


## User revised planned sample and local clock

User explicitly increased20games to50games, then reduced120seconds to60seconds. Latest local screen standard is25pairs,60000+500,oneworker. Do not interpret this as evidence that the external competition clock changed. Final reports must state actual tested conditions.

No20-to50 extension supervisor was launched before the clock revision. Instead stopped all eight120second compiled screen process trees after verifying exact command lines/root identities (roots17956,33196,9308,33660,14880,33156,13012,13252;49ownedprocesses total). All eight observation handles ended intentionally with exit1. Preserved all completed120second records and wrote protocol_change.json in each stopped run. Do not resume stale writer locks. Older two neural-candidate futility stops remain historical20game decisions, not an assertion that they cannot meet a50game target.

Started eight FRESH60second50game comparisons, explicit --pairs25 --base-ms60000 --increment-ms500 --workers1 --bank screen --record-games; Skill7 explicitly set forStockfish. All eight manifests verified60000/500/oneworker and intended candidate/opponent. campaign_60s_50g.json records full paths, seed and handles:
-42737 compiled_pvs_01_silky_60s_50g
-2071 compiled_pvs_01_sf7_60s_50g
-10622 compiled_ordered_01_parent_60s_50g
-46693 compiled_sf7_rl_01_parent_60s_50g
-93758 compiled_sf7_rl_01_silky_60s_50g
-57821 compiled_sf7_rl_01_sf7_60s_50g
-40388 compiled_ordered_01_silky_60s_50g
-69028 compiled_ordered_01_sf7_60s_50g

Candidate runtime/weights are unchanged. Live manifests, not historical candidate freeze metadata, specify this revised TC. No results from different clocks are pooled.50game target point thresholds:35points vs silky,25actualwins vsSF7; parent comparisons are diagnostic. Independent confirmation remains separate from these observed screen banks. No promotedcandidate/ZIP.

Also corrected tools/analyze_recorded_game.py to read initial clock from adjacent manifest (or explicit --base-ms), removing the hardcoded10second assumption. Reviewed one compiledPVS/silky sbank062white loss with offline50knodeSF20; estimated significant loss atply60Qf2vsQxa3 and later lost-ending mistakes. Saved compiled_core_01/loss_sbank062_white_50k.json. Bounded oracle diagnosis, not training/qualification ground truth.


## Revised-campaign health and packaging preflight

Previous goal turn made progress: user-authorized protocol migration from120s/20games to60s/50games, preserved old records and launched eight fresh runs. Current eight session handles confirmedlive twice; no restart from observation timeouts.

Refetched current official rules/agent contract with curl after web-reader errors, saved release_rules_20260908.md/release_contract_20260908.md. External competition still120s+0.5s; user's current local screen protocol remains60s+0.5s. Never label local60second results as120second results.

Added tools/audit_candidate_package.py, using unmodified harness.package.members to audit prospective contents without writing a ZIP. All three compiled candidates exactly match frozen runtime manifests, include agent.py and weights, pass static import/file/JIT-setting checks, and are165570/167308/165570bytes unzipped respectively. package_preflight_01.json is static preflight only, not smoke, full compliance certification or promotion. No archive created.

Added tools/campaign_status.py: audits every configured run and distinguishes score from actualwins; marks screen gates only after50recorded games and report_50.json with no failures. Requires>=70%score on silky and>=50%actualwins onSF7 for the same candidate; never promotes from partial rates. Snapshot campaign_snapshot_60s_01.json is descriptive only.

Targeted ruff and strict mypy --follow-imports skip passed on audit_candidate_package.py,campaign_status.py,audit_recorded_screen.py,freeze_compiled_value.py,check_compiled_value.py after annotation fixes. This is not a claim that the full repository gate passed. No live runtime or orchestration hash changed.

Latest completed pairs in revised60s campaign: PVS/silky42737 .5/2; PVS/SF7 2071 1/4points(two draws/two losses); ordered/parent10622 0/2; RL/parent46693 2/2; RL/silky93758 0/2; RL/SF7 57821 0/2; ordered/silky40388 0/2; ordered/SF7 69028 2/2. All tiny partial samples; no candidate selected, no targets proven. Current plan remains25pairedopenings percomparison. Continue live games, then diagnose/iterate based on matched results.


## Verified wait and runtime-memory observation

Previous turn was progress (packaging preflight, audited scoreboard and targeted typing checks). This turn explicitly polled all eight current60s/50game handles twice with45second bounded waits; every handle remainedlive and several new pairs completed. No restart or candidate mutation.

Read-only Windows process observation of current compiled runners saved runtime_memory_snapshot_01.json. Observed process lifetime peak working sets: PVS213.4MiB, ordered215.4MiB, RL213.0MiB. These are local observations, not a full platform memory-limit certification.

Audited updated campaign_snapshot_60s_02.json: runtime/harness/orchestration hashes, PGNs and clocks pass for recorded games. Snapshot total games bycomparison: PVS/silky4 (.5points), PVS/SF7 five(0wins3draws2losses), ordered/parent4(1win1draw2losses), RL/parent3(2wins1draw), RL/silky4(1win3losses), RL/SF7 five(0wins5losses), ordered/silky3(1win2losses), ordered/SF7 five(4wins1loss). Unpaired completed games are included in these descriptive totals; complete-pair counts remain in underlying audits. None has completed50games, so all observed-screen gate flags remainfalse. Do not select a champion from these small/mixed samples.

All eight sessions remain those in campaign_60s_50g.json; no new training or archives started. Continue matched games before combining mechanisms or selecting the next RL parent. Goal remains unachieved and active.


## Dead-writer recovery and campaign resume (2026-09-08 ~14:05)

All eight 60s/50game screens were found STALLED: last game files 13:38-13:40, zero live python/stockfish processes, all eight writer.lock PIDs verified dead via Get-Process (1, 8, 5228, 9124, 16532, 17952, 22832, 32260, 36816 all dead). Frozen candidate manifests re-verified ALL MATCH (11 files x3 candidates); harness + orchestration hashes UNCHANGED vs run manifests; no MILKYWAY_* overrides; interpreter 3.12.13 matches.

Stale locks removed (owners verified dead per protocol), all eight relaunched with byte-identical protocol (--pairs 25 --workers 1 --bank screen --base-ms 60000 --increment-ms 500 --record-games --seed default 20260906, --stockfish-level 7 on SF runs). candidate_screen.py is resumable: loads pairs.json, plays only pending positions. All eight recreated writer.lock with live owners (31880, 19052, 6800, 29988, 23564, 37948, 14488, 39060); ~50 python workers + 3 stockfish burning CPU. Launchers/logs in Temp opencode resume_60s (not in repo). No results pooled across clocks; no qualification claimed.

## Resume verified + snapshot 03 (2026-09-08 ~14:20)

All eight resumed runs completing games (snapshot campaign_snapshot_60s_03.json via tools/campaign_status.py, all gates false, not_a_promotion). Partials: pvs_silky 9.0/16 (0.562), pvs_sf7 2W/23 (0.087 win), ord_parent 7.5/15, rl_parent 7.5/15, rl_silky 8.0/16, rl_sf7 0W/21, ord_silky 8.0/16, ord_sf7 5W/21. Futility check vs 50-game targets (35 pts silky / 25 wins SF7): every run still mathematically alive (maxima 29-43), so no stops. rl_sf7 needs 25 of remaining 29 (nearly impossible, not yet impossible). No candidate selected, no ZIP.

## Futility stop: PVS vs SF7 (2026-09-08 ~14:45)

Poll showed compiled_pvs_01 vs SF7 at n=30, W2 D8 L20 (score 0.200, win rate 0.067). Max reachable wins 22 < 25 gate: mathematically dead. Recount confirmed 30 games immediately before action. Stopped ONLY the verified tree: lock owner PID 29988 command line matched the resumed pvs_sf7 launch exactly; killed its 5 descendants (2 runner shims, 2 runners, 1 stockfish) plus 29988; shim parent 24512 exited on its own. All 7 sibling run owners re-verified alive afterward. 15 pairs / 30 game files consistent, no orphan partial. futility_decision.json written in run dir; games/pairs/manifest immutable; stale lock preserved as do-not-resume marker. No candidate, harness, or tool file changed.

Remaining live: 7 runs. Tightest: RL vs SF7 needs 23/23 (alive on the line), ordered vs SF7 needs 19/22, PVS vs silky needs 24.5/29, RL vs silky 23/28, ordered vs silky 23.5/28. No qualification; no ZIP.

## Poll cycle 3 + three mathematical-futility stops (2026-09-08 ~14:55)

Fresh snapshot campaign_snapshot_60s_04.json then immediate recount campaign_snapshot_60s_05.json right before acting. Three more target screens died mathematically since the last poll (all three had "must-win nearly perfect" requirements that were not met):

- RL vs SF7: n=35, W3 D10 L22. Max reachable wins 3+15=18 < 25 gate. Dead.
- ordered vs silky: n=27, W10 D3 L14 = 11.5 pts. Max reachable 11.5+23=34.5 < 35-pt gate. Dead.
- ordered vs SF7: n=33, W6 D8 L19. Max reachable wins 6+17=23 < 25 gate. Dead.

Stops executed ONLY on these three: verified each stale-to-act lock owner's full command line matched its resumed launch exactly (RL/SF7 PID 14488, ordered/silky PID 6800, ordered/SF7 PID 19052), then taskkill /T /F per root: 14488+5 descendants (6512,15044,18640,23276,6100), 6800+4 (17312,3848,39248,2516), 19052+5 (18600,41052,3424,6236,8264) — 17 processes total, no other PID touched. All four sibling owners re-verified alive afterward with matching command lines (23564 pvs_silky, 39060 rl_silky, 31880 ord_parent, 37948 rl_parent); zero stockfish processes remain (all three SF7 screen trees now stopped). Each stopped run has exactly one in-flight orphan partial (uncommitted white game: sbank_078_white, sbank_032_white, sbank_052_white respectively) preserved for audit and named in its futility_decision.json; completed pairs/games/manifest immutable; stale writer.locks preserved as do-not-resume markers. No candidate, harness, or tool file changed.

Remaining live: 4 runs. Target screens: PVS vs silky n=26, 13.5 pts, needs 21.5/24 (89.6%); RL vs silky n=27, 13.0 pts, needs 22/23 (95.7% — alive on the line). Parent comparisons (diagnostic, no gate): ordered vs parent n=23, 12.5 pts; RL vs parent n=24, 14.0 pts. No qualification; no ZIP; no candidate changes, retraining, combining, or packaging.

## Search V2 accepted: state recovery, two further futility stops, audit and handoff

2026-09-08. Latest explicit user attachment changes strategy to original Search V2; pause blind RL/value cycling. New authoritative documents: experiments/search_v2/IMPLEMENTATION_PLAN.md and CONTINUATION_PROMPT.md. No baseline has been selected yet; BASELINE_MANIFEST.json records selection_pending and verified identities for PVS, ordered, RL and exact silky runtime.

Independently verified main HEAD834ceb88fa1f32cd242431bc1be171f9ecaaad7a, existing dirty tree, all prior60s futility decisions, current manifests and process trees. Snapshot06 showed remaining silky targets mathematically dead. Immediately recounted and stopped ONLY verified PVS/silky owner23564 with4 descendants (17W6D16L in39,20points,max31<35) and RL/silky owner39060 with4 descendants (17W3D20L in40,18.5points,max28.5<35). Their detailed futility_decision.json records UTC time, full root command, descendants, threshold arithmetic and orphan records. All game/pair/manifest files and stale locks preserved. Do not resume these or any other futile run.

Two parent writers remain:31880 ordered/PVS and37948 RL/PVS, full identities saved in search_v2/parent_process_snapshot.json. Latest audited snapshot07: ordered18W9D11L in38 (22.5points), RL19W6D13L in38 (22points). Parent diagnostics have no promotion futility gate. Let both reach50 games; no new heavy tournament or training launched. All three candidates are ineligible for promotion, but formal eight-run closeout waits for parent completion. No new agent.zip.

Completed source audit of compiled board/search/PVS/ordering/time paths and relevant silky search sections. Compiled path lacks most selective search; qsearch always generates full legal moves; existing tt_hits means cutoffs; conservative TT/context/hash cost needs measurement. ARCHITECTURE_AUDIT.md separates absent, weak, suspicious and tested features. Official Berserk/Ethereal/Viridithas README descriptions reviewed at architecture level; no third-party implementation or net copied. Canonical competition rules/contract freshly retrieved directly after browser fetch errors, saved under search_v2.

Prepared SEARCH_METRICS.md/JSON specification, not fake telemetry results. Frozen240-position development suite with legal histories/source hashes, including105 recorded-loss positions,33 check evasions,17 promotion positions and118 endings (categories overlap). SHA256 b8bf9134c965521324c9cf7231c16c0fdaf079376f8d25249bb0a314f169aa01. Independently replayed all histories, verified all240 unique valid nonterminal positions and source hashes; probe_suite_verification.json. Builder ruff passed. Broad instrumented search remains pending selected baseline. Prior depth6 LMR output exists; no rerun despite expired handle. Four cases saved nodes but two scores changed; no strength claim.

All eight recorded-game audits passed hash/PGN/clock validation (snapshot07); RECOVERY_AUDIT.json contains detailed earlier audit. Frozen runtime/weights/harness/orchestration unchanged. Only new Search V2 preparation, new futility decisions, snapshots and documentation changed in this turn. No repository-wide test or platform qualification claimed. Development60s+0.5s/50games; final independent120s+0.5s/100games pertarget.

Next: finish parent diagnostics; write campaign_closeout_60s_01.json and CAMPAIGN_REJECTION_60S.md; select/freeze a canonical baseline; add parity-checked diagnostic counters and run the240-position suite; only then freeze one isolated search improvement and start parent/SF7-first screens. Detailed plan includes later conditional RL, independent qualification and deterministic extracted-ZIP verification.

## Revised promotion objective and Search V2 tournament controller

Latest user instruction supersedes the old goal: >=70% ACTUAL WINS against exact live silky_snow is primary; prove superiority over the three current compiled challengers. SF7 no longer has a mandatory win-rate gate. TOURNAMENT_PROTOCOL.json records the frozen roster and conditions. Development requires35wins/50games; final independent confirmation70wins/100games at120s+0.5s, plus challenger comparisons and reliability. Draws count toward score only, not the live win gate.

Completed LMR broad probe:240/240 disabled-path move/score/depth/node parity cases; all240 enabled comparisons completed depth5. Work10134358->6847068nodes (32.4% reduction),14movechanges,16scorechanges. Counter invariants passed. Offline SF20 forced-move100knode diagnosis of14changed decisions found no delta worse than-100cp (nor better than+100cp); bounded diagnosis, not strength. Engine remains offline-only.

Completed staged-quiescence probe:240/240 fixed-depth scores match; independently verified full legal and capture/promotion sets against python-chess. Work essentially unchanged10134358->10134445nodes, measured time40.42->23.67seconds under concurrent old parent games (~41% reduction; not controlled timing). Full check evasions, quiet promotions and terminal-before-standpat handling retained.

Both original-code interface prototypes passed80low-clock moves, legal fallbacks, history reconstruction/reset and120second allocation probes. LMR import22.25s/max250ms-clock move51.73ms/fullclock6.50s; staged import25.75s/max51.50ms/fullclock4.69s. No new engine/model copied. Old frozen candidates, weights and harness unchanged. Prototype source/weight hashes and verification reports live under search_v2. Relevant new orchestration/probe lint passes; no full-repository gate claim.

New tournament controller tools process: session3266, command .venv/Scripts/python.exe experiments/search_v2/run_candidate_tournament.py. Its state is candidate_tournament_01.json. Currently waits for both existing parent diagnostics to finish (last observed ordered43games, RL44games). It verifies owners rather than trusting expired original handles, closes all8oldruns, selects ordered as engineering baseline only after completed positive parent result, freezes verified LMR/staged siblings, then runs sequential50game parent/live/PVS/RL comparisons. Parent/challenger screen continuation55%score; live70%actualwins. It stops only its own verified live-screen tree when35wins becomes mathematically impossible, preserving evidence. It never packages/promotes automatically. Do not duplicate this controller or its writers. If both variants survive, compare them directly before final champion selection. If both fail, next measured iteration remains required; no claim of achievement.

Recurring continuation is ACTIVE in this task: automation continue-search-v2-candidate-improvement, every30minutes. It checks controller/process/results before acting, continues development after batch completion, and pauses only after verified goal/artifact completion. Remain quiet on unchanged jobs. This supplies ongoing continuation while the older goal record remains usageLimited and contains obsolete SF7/score criteria; user revision is authoritative.

Next: let old parent diagnostics settle; controller freezes/launches first new screen automatically. Watch for controller errors. Continue measured search improvements after results; no new agent.zip until qualification.

## Verified continuation wait and measured search bottleneck

Previous turn made progress (two verified search prototypes, revised tournament controller and recurring continuation). This turn confirmed controller session3266 live through repeated polls including a45second bounded wait. Get-Process independently confirms existing parent owners31880/37948 alive; both parent comparisons advanced to46recordedgames/23committedpairs. No missing handle, restart, stopped writer or new candidate mutation. Sandbox CIM inspection was denied, but supported session/process checks provide live evidence; no escalation needed for this wait.

Aggregated completed240-position search counters into SEARCH_METRICS.md:91.53% of10,134,358visitednodes are quiescence entries;312.7million legal moves generated vs10.13million children searched. Existing independently tested staged generation directly addresses that measured work. Keep neural retraining deferred pending search tournament outcomes. Goal remains unachieved; controller will close old diagnostics and launch verified variants when both50game reports exist.

## Old campaign closed; Search V2 candidate screens live (2026-09-08 ~16:26)

Both parent diagnostics completed 50/50 with reports and zero failures: ordered vs parent 25W11D14L (30.5 pts, 50.0% actual wins), RL vs parent 25W7D18L (28.5 pts, 50.0%). Controller session verified owners each cycle, then wrote experiments/compact_cycle_01/campaign_closeout_60s_01.json and CAMPAIGN_REJECTION_60S.md (16:26): all eight runs terminal, six futility stops preserved, generation formally rejected, no ZIP.

Baseline selection assert passed (ordered parent score > 50% at 50 games); BASELINE_MANIFEST.json updated to selected and frozen with completed parent evidence. Verified LMR and staged interface runtimes frozen byte-identically into experiments/search_v2_lmr_01 and search_v2_staged_01 with new manifests. First candidate screen launched and playing: search_v2_lmr_01 vs compiled_ordered_01 (lmr_parent_60s_50g, 50 games, 60s+0.5s, seed 20260906, controller-owned). Sequential gates per protocol: parent/challenger >=55% score, live silky >=70% actual wins, automatic futility stop when 35 live wins becomes impossible. Next opponents queue automatically; staged variant follows lmr. If both survive, compare them directly before champion selection. No qualification or ZIP claim; goal remains active.


## Development speed revision: fast clock + concurrent games (2026-09-08 ~16:55)

User directed faster games (~30 seconds each, moves very fast) and continuation. Changes, all recorded in TOURNAMENT_PROTOCOL.json and CONTINUATION_PROMPT.md:

- Development clock reduced 60s+0.5s to 12s+0.1s (1/5 scale) for candidate tournament screens. The partial 60s lmr parent screen (4 games) is preserved at lmr_parent_60s_50g_superseded_partial with SUPERSEDED_NOTE.json and is never pooled with fast-clock games.
- Measured constraint: per-game wall time has a ~40s structural floor. harness/runner.py agents are fresh processes per game and every kernel is @njit(cache=False); the harness sandbox points NUMBA_CACHE_DIR at a per-game scratch dir wiped between games, so compilation cannot persist. Measured runner startup-to-ready 19.8s per agent; harness is frozen and untouched.
- To meet the ~30s/game effective target, workers_per_comparison raised 1 to 3 in run_candidate_tournament.py (WORKERS=3): three independent games play concurrently, one completes every ~25 seconds on average (measured 7 to 10 games in ~90 seconds). Clock, bank, seed, pairing and record-games unchanged; games remain independent and pooled within the same screen.

## Goal lowered to 10% over live; aspiration variant added (2026-09-08 ~17:20)

User revision: minimum acceptable result is now a candidate better than the exact live silky_snow by at least 10 percentage points of score (>=0.55/50-game score), plus superiority over the three compiled challengers; the 70%-actual-wins live gate is withdrawn. "Try all legal methods" is standing direction. Changes:

- Controller live gate changed to all_recorded_score >= 0.55; live-screen futility stop now fires when 27.5/50 points becomes mathematically impossible (points-based arithmetic replaces the 35-wins rule). TOURNAMENT_PROTOCOL.json and CONTINUATION_PROMPT.md updated.
- lmr parent screen COMPLETED 50/50: 29/50 points (0.58) >= 0.55 gate, PASSED. Controller advanced automatically to the live screen lmr vs silky_snow (12s+0.1s, 3 workers). Early live standing 9.5/12 points (79%) is a small sample, not evidence of qualification.
- NEW legal variant implemented: aspiration windows on the ordered baseline. Isolated runtime experiments/search_v2/aspir_interface_runtime (frozen parent files + new aspir_search.py with root window +/-45cp around the previous exact score and immediate full-window re-search on fail; agent.py import switched). No frozen file touched; compiled_ordered_01, lmr and staged runtimes byte-identical.
- Verification (verify_aspir_variant.py, results in aspir_verification_01.json): 30 suite positions at fixed depth 5, ZERO root-move disagreements vs baseline; mechanism engaged (16 re-searches); zero low-clock get_move failures at 250ms; 40-move sequential self-play fully legal; node work 102.2% of baseline at depth 5 (savings expected only at deeper iterations). Verification gates passed; no strength claim.
- Frozen byte-identically into experiments/search_v2_aspir_01 (prepare_aspir_freeze.py wrote aspir_freeze_manifest.json; freeze_candidates verifies hashes). Tournament roster now lmr, staged, aspir - each runs parent, live silky, pvs, rl screens sequentially with early rejection.
- Controller upgraded: completed screens are re-audited and reused instead of relaunched; restart-safe. Restarted cleanly at ~17:15; live screen resumed without losing completed games.


## lmr and staged pass their screens; live gates crushed (2026-09-08 ~19:05)

Development screens at 12s+0.1s/50 games, 3 workers, gates >=0.55 score. Completed results, all with zero unhealthy terminations:

- lmr: parent 29/50 (58%) PASS; live silky 39/50 (78%) PASS; pvs 31/50 (62%) PASS; rl 31/50 (62%) PASS. All four gates cleared. Termination mix healthy (42 checkmate, 6 threefold, 2 fifty-move).
- staged: parent 32.5/50 (65%) PASS; live silky 43.5/50 (87%) PASS; pvs screen running (21/50 at ~19:02); rl pending. Termination mix healthy.
- aspir: queued after staged.

Both surviving variants far exceed the revised 10-point goal (78% and 87% vs live are +28 and +37 points over parity). Per protocol they will be compared directly before champion selection, and the winner still needs the independent 120s+0.5s/100-game confirmation per opponent on exact frozen runtimes before any promotion or ZIP. No qualification claimed yet; development evidence only.

## Full development tournament results (2026-09-08 ~20:40)

Controller status: screens_finished. All screens 50 games, 12s+0.1s, seed 20260906, paired colours, zero unhealthy terminations. Candidate-perspective WDL and scores:

| Candidate | vs parent | vs live silky | vs pvs | vs rl | Verdict |
|---|---|---|---|---|---|
| lmr | 24/10/16 = 29/50 (58%) PASS | 35/8/7 = 39/50 (78%) PASS | 25/12/13 = 31/50 (62%) PASS | 27/8/15 = 31/50 (62%) PASS | all four gates cleared |
| staged | 28/9/13 = 32.5/50 (65%) PASS | 41/5/4 = 43.5/50 (87%) PASS | 35/6/9 = 38/50 (76%) PASS | 26/11/13 = 31.5/50 (63%) PASS | all four gates cleared |
| aspir | 22/2/26 = 23/50 (46%) FAIL | not reached | not reached | not reached | rejected at parent gate |

## Confirmation campaign live and verified after session handoff (2026-09-08 ~21:10)

Previous goal session hit its usage limit at ~21:04; all protocol artifacts survived and the confirmation screen survived as a detached process. Verified state:

- Champion: search_v2_staged_01 (won tiebreak 23W/10D/17L = 0.56 vs lmr; CHAMPION_SELECTION_01.json, runtime hashes recorded, not promoted).
- Live confirmation RUNNING and identity-verified: PID 6512 tools/confirmation_screen.py, exact predeclared protocol (staged vs experiments/silky_snow, frozen unseen bank confirmation_bank_01_frozen.json sha f87d33b5..., 50 pairs/100 games, 120000+500ms, workers 1, seed 2026090822, record-games). Gate: >=60% score vs live; then five remaining opponents (lmr, ordered, pvs, rl, aspir) with paired-bootstrap 95% lower bound > 0.5, max 2 concurrent; stop on any reliability failure; no early positive stop; no ZIP until all gates.
- First completed game: fresh_confirm_007_white, staged won by checkmate from the fresh independent bank. Manifest records evidence_type and fresh_independent_confirmation bank with full harness/orchestration hashes.
- 100 sequential games at full clock will take several hours; no babysitting required, resumable by design. Exclusion index (903,252 previously exposed positions) and bank final audit already passed (confirmation_bank_final_audit_01.json).

No candidate is qualified yet; no ZIP exists. Next: let the live confirmation run to 100 games, then launch the five challenger confirmations (max 2 concurrent) and apply the bootstrap gate; then packaging gates.


## Staged live confirmation STOPPED on a flag fault at 48.6% (2026-09-09 ~10:25)

Overnight self-review found the live confirmation at 35/100 games, W14 D6 L15 = 48.6%, below the 60-point gate with the drift 68% -> 60% -> 58% -> 54% -> 51.5% -> 48.6%. Worse, one game (fresh_confirm_009_white.json) recorded termination "flag": the staged candidate overran its own clock and the watchdog awarded the game to silky. Per harness/referee FAILED_TERMINATIONS = {"crash","illegal","flag","init","both_failed"} and the predeclared CONFIRMATION_CAMPAIGN_PROTOCOL stop_on_reliability_failure, this is a disqualifying reliability failure, independent of the score. Note the flag was the candidate's own time fault, not a referee error; full-clock time management is part of what confirmation tests.

Actions taken: verified the writer's full command line matched the predeclared confirmation launch exactly (PID 6512, confirmation_screen.py, staged vs silky, frozen bank, 120000+500, 50 pairs, seed 2026090822), then taskkill /T /F on 6512: 5 processes total (writer + 4 runners, incl. the live in-flight game). All four sibling processes are dead; zero python processes remain. Completed games and the in-flight flag game preserved (flag game uncommitted to pairs.json, one orphan: fresh_confirm_009_white.json); futility_decision.json written inside confirm_staged_live_120s_100g with full WDL/termination breakdown. Stale lock left as do-not-resume marker. Frozen candidate, harness, bank unchanged. Do NOT resume this screen.

New candidate work (started per the user's find-a-new-candidate direction, all legal original search work):
- Built combined staged+LMR variant in NEW isolated runtime combined_interface_runtime: byte-identical frozen-parent files except core.py (staged capture-only movegen passthrough, 2 lines), new combined_search.py (LMR reduction block merged onto the staged movegen; fully diff-audited: combined is staged+exactly-the-LMR-block, lmr+exactly-the-staged-block, verified both directions), agent.py one-line import switch to combined_search. No frozen file edited.
- Verification (verify_combined_variant.py, results combined_verification_01.json): 30 fixed-depth suite positions, 18,950 reductions + 37 re-searches (both mechanisms engage), 34.4% fewer nodes than baseline, only 2 move disagreements with worst delta -3cp (one is the same mate-score position), zero low-clock failures at 250ms, 40-move sequential self-play fully legal. Verification gates passed; freeze manifest written (combined_freeze_manifest.json, hash-verified).
- Tournament controller extended to freeze and queue "combined" after aspir; exercised freeze_candidates() end-to-end: roster now [lmr, staged, aspir, combined] with experiments/search_v2_combined_01 manifest mechanism=staged_lmr_combined.
- Exclusion index refreshed to cover the new candidate's provenance: build_confirmation_exclusions.py now reads search_v2_combined_01_manifest.json and pins its 12 file hashes as zero-record provenance sources (assertion fails the whole build if any frozen byte differs). Old index archived as *_superseded_20260909. Refresh completed: 909,786 unique piece placements from 1,597 sources (up from 903,252/old count), combined files confirmed among sources. Builder keeps a --refresh explicit flag; default run still refuses to overwrite.

Standing: no qualified candidate; no ZIP. Staged is confirmed disqualified for this bank (flag + sub-gate score); its 35 games stay diagnostic. Combined variant is verified-safe and frozen pending tournament play once the user decides the next roster. The 48.6% full-clock result versus 87% fast-clock is the key scaling evidence to beat.
Both lmr and staged far exceed the revised goal (>=55% vs live = 10-point improvement): staged scored 87% (+37) and lmr 78% (+28) against the exact live silky_snow, with 76%/62% and 63% superiority over the pvs and rl challengers. aspir never engaged its benefit at the fast clock's shallow depths and failed its parent screen honestly; preserved as evidence.

Next per protocol: direct staged vs lmr comparison launched (direct_staged_vs_lmr_12s_50g, 50 paired games, same clock/seed) to select the champion. The winner must still pass independent confirmation (120s+0.5s, 100 games per opponent, unseen bank, exact frozen runtimes, zero reliability failures) before any promotion or agent.zip. These development screens are fast-clock screening evidence, not qualification.
No qualification; no ZIP. Next: live screen resolves (~25s/game effective), then pvs/rl for lmr, then staged and aspir rosters. Any candidate passing all four screens proceeds to the 120s+0.5s/100-game independent confirmation on exact frozen runtimes.
- Controller made restart-safe: archives prior candidate_tournament_01 state, skips the already-written closeout, reuses verified frozen candidates, resumes existing screens instead of asserting fresh dirs, appends to existing logs.
- One stale writer.lock in lmr_parent_12s_50g was removed only after verifying its owner PID 40072 was dead (killed screen tree). Controller briefly recorded attention_required from that stale lock; restarted clean.

Current state: controller live, lmr_parent_12s_50g resumed at 12s+0.1s with 10 games complete, all terminations healthy (8 checkmate, 2 insufficient_material; zero flags/crashes/illegal). Remaining tournament queue (lmr live/pvs/rl, then staged all four) now estimated ~20 minutes per comparison instead of ~2 hours. Gates unchanged: parent/challenger >=55% score, live silky >=70% actual wins, automatic futility stop; independent confirmation remains 120s+0.5s/100 games on exact frozen runtimes. No qualification; no ZIP.
## Independent verification of completed fast screens and confirmation provenance

Verified all nine completed development screens from saved PGNs, clocks and current runtime/opponent/harness/orchestration hashes, not just reported table. Every completed manifest specifies12000ms+100ms,3workers,50games. Results match the user table. Actual live wins are LMR35/50=70%, staged41/50=82%; scores are78% and87%. New evidence file: search_v2/verified_development_results_01.json. Aspiration46% parent score is verified, but attributing failure specifically to re-search cost remains an inference, not a controlled causal ablation.

Direct staged/LMR comparison is live: writer20016 exists with matching launch-era start time, raw records initially6games4W0D2L. Not enough evidence to select champion; no restart. Previous goal turn was a verified wait with new counter evidence; this turn independently verified completed results and advanced confirmation preparation.

Important protocol inconsistency:55%score is5percentagepoints above50%, not10percentagepoints. Latest user's '+10points' description conflicts with saved55%development wording, while confirmation JSON still says70actualwins. A concise asynchronous question asks whether final target is60%score or70%actualwins. Do not silently resolve conflicting final gates or launch expensive final qualification on an unacknowledged relaxed rule. Both current fast live results pass either threshold; full-clock results remain missing.

Confirmation provenance inventory saved at search_v2/confirmation_provenance_inventory_01.json. Existing confirm bank appears in4earlier manifests (confirm_validate, silky_snow_confirm, silky_snow_promo, r34/speed_confirm_vs_checkpoint); it cannot simply be called untouched. NPZ array inventory is recorded for follow-up exclusions in addition to earlier JSONL data audit. Prepare a fresh independent bank and audit overlap/provenance before final confirmation; no model/candidate/playing files changed. No promotion or agent.zip.

User explicitly resolved final threshold:60%score against live. Updated protocol removes stale70actualwins field. Confirm100games/120s+0.5s, independent bank, challenger superiority and reliability remain required. Actualwins are reported separately.
`nAutomation state correction: attempted to update continue-search-v2-candidate-improvement to the confirmed60%score gate. App reports automation no longer exists (possibly deleted); no automation.toml exists locally. Did not recreate a potentially user-deleted automation. Do not claim30minute scheduled continuation is active. Continue via the active thread goal; actual direct-match process remains separate.`n

## Confirmation exclusion index completed

Previous goal turn made progress by resolving the final60%score gate. This turn verified direct-match owner20016 live; tiebreak advanced from15 to24savedgames during preparation, no restart or candidate mutation.

Built search_v2/confirmation_exclusions_01.sqlite with903,252unique piece placements from1,523source entries:313NPZ files plus JSONL datasets, historical game trajectories and experiment bank manifests. Source hashes and index hash saved in confirmation_exclusions_01.json. Uses packed12absolute-colour piece planes, conservatively ignoring side/rights/clocks. Confirmed feature-only tuning_master_value_v2 derives from indexed master_value_v2 tensors by reading build_tuning_npz.py. SQLite integrity, index hash/count and20known training-position lookups passed; builder ruff clean. No need to regenerate this immutable snapshot.

CONFIRMATION_BANK_PROTOCOL.json now predeclares50fresh positions, seed2026090821, offlineSF-only trajectory selection (no candidate evaluation), fixed balance filter, exclusion of both exact and mirrored placements, and100paired-colour games peropponent at120s+0.5s. Final live score gate60%; actualwins separate. Refresh overlap against tiebreak records created after this index before accepting bank. Index is a data-exposure check, not a claim that an independent bank already exists.

Next: generate and audit the new bank using completed index; finish direct staged/LMR match, freeze champion and predeclare full confirmation roster/gates. No qualification or agent.zip yet. Goal remains active.

## Staged selected; independent full-clock confirmation launched

Previous goal turn made concrete progress (completed exclusion index). This turn generated50fresh openings from176seeded offlineSF trajectories using predeclared protocol2026090821, with no candidate evaluation. Default sandbox blocked Windows engine pipes before generation began; approved local process execution succeeded. Output confirmation_bank_01.json records generator/protocol/index/binary hashes, source moves, balance checks and rejections. No engine data is added to candidate runtime.

Direct staged/LMR match completed50games: staged23W10D17L,28/50points=56%, zero unhealthy terminations. Pair-aware95%score interval44–68% is inconclusive about population superiority. Staged selected for confirmation on completed head-to-head result, not declared promoted. CHAMPION_SELECTION_01.json records exact runtime hashes and audited match.

Final bank audit passed: all indexed source hashes stable;50legal unique balanced positions; zero exact or colour/rank-reflected overlap with903,252indexed placements;26post-snapshot game records independently replayed with no overlap. Bank frozen in confirmation_bank_01_frozen.json, SHA256 f87d33b5d55fa01d4abe59f62b9fcbf32641c5b9b020ba66a0306bc3ebd0b867. Final audit and generated source remain separate immutable evidence.

Added separate tools/confirmation_screen.py, leaving original playing/tournament runner and harness untouched. Enforces50pairs/100games,120000+500ms,1worker, recorded games and frozen audited bank; hashes its own orchestration and bank file. Ruff and targeted strict mypy passed. Staged package preflight matches its frozen runtime (177452bytes); this is not archive/smoke/platform qualification.

LIVE full-clock run: experiments/search_v2/confirm_staged_live_120s_100g; session78043, writerPID6512. Approved local subprocess execution; manifest verified120000+500,1worker,50pairedpositions, fresh bank, exact staged runtime hashes. Session polled and confirmed live after launch. State/queue in confirmation_campaign_01.json. No concurrent training or development compilation. Live gate is60%score; actualwins reported separately.

After live pass: confirmation against LMR, ordered, PVS, RL and aspiration under same frozen bank and100game protocol, maximum2concurrent comparisons with1worker each. Other-candidate gate remains paired-bootstrap95%lower score bound>50%, with20000resamples/seed2026090823. Includes the rejected aspiration entrant so superiority is checked directly, not assumed transitively. No early positive stopping. CONFIRMATION_CAMPAIGN_PROTOCOL.json records full roster and selection/gates. On any failure preserve evidence and continue measured development with a new unseen confirmation bank when needed.

No qualification, archive replacement or upload. Next inspect live run progress/records; once complete audit against60%score and reliability gate, then proceed through queued opponents. Do not duplicate or restart a live writer.

## Combined development resumed (2026-09-09)
Read latest user handoff and staged disqualification record. Corrected stale confirmation_campaign_01 status: staged run must never resume. Verified all 12 combined runtime hashes against frozen manifest. Launched combined vs ordered parent screen, 50 games, 12s+0.1s, 3 workers, seed 20260906, recorded games; session 32785. State in combined_campaign_01.json. Final live gate remains 60% SCORE (55% is only the parent development screen). Existing low-clock checks do not establish full-clock reliability; staged flag diagnosis and full-clock regression testing remain necessary before another independent confirmation. No qualification or ZIP. Old confirmation bank is exposed and cannot qualify a subsequently selected candidate.

## Clock-failure diagnosis prepared
Combined parent screen confirmed live via session32785; first3 completed pairs score3/6, all6 terminations healthy. Too early for strength conclusions. Read failed staged PGN: last white clock55.751s, next request after24...Nf6 flagged. Search tick checks every128nodes; allocator hard ceiling12s in this clock range. Therefore ordinary low-clock exhaustion is not established; actual failure cause remains unknown. Preserve disqualification; do not relabel as infrastructure failure without evidence. Added tools/replay_clock_failure.py (ruff and strict targeted mypy pass), replaying historical candidate requests plus failed position through unchanged sandbox, with clocks, hashes, legality, elapsed times and stderr. No candidate/harness edits. Run sequentially after current screen to avoid new compilation load: .venv/Scripts/python.exe -m tools.replay_clock_failure --agent experiments/search_v2_staged_01 --record experiments/search_v2/confirm_staged_live_120s_100g/games/fresh_confirm_009_white.json --out experiments/search_v2/staged_flag_replay_01.json . Then equivalent combined replay. This is diagnostic only and does not qualify either runtime.

## Automatic combined continuation launched
Previous goal turn made progress: prepared clock replay and verified active screen. Current turn added tools/continue_combined_campaign.py, passed ruff and targeted strict mypy, and launched session20981 via approved local subprocess execution. It waits for existing parent report plus writer exit (never duplicates parent), audits50games, requires55%parent score, then runs staged/combined clock replays sequentially and requires combined replay legality/timing. Subsequent50game fast screens: live60%score; PVS,RL,staged,LMR,aspir55%development score each. Every completed match audited; a failed gate stops continuation for new development. No promotion or ZIP; full-clock reliability and fresh100game confirmation still required. State combined_continuation_01.json. Parent session32785 confirmed live and advanced to6completed pairs (9/12points), no failed terminations in those pairs. This is partial development evidence only. Do not launch duplicate comparisons while continuation is active.

## Combined packaging preflight and rules refresh
Previous goal turn progressed by launching automatic continuation. This turn confirmed both session32785(parent) and20981(continuation) live. Static package audit passed against frozen combined manifest:178701bytes, exact file hashes, allowed imports, no native binaries or cache/parallel flags found by AST preflight. Evidence combined_package_preflight_01.json; does not prove provenance by itself or replace extracted artifact tests. Official rules and agent contract fetched20260909 after approved HTTPS access outside sandbox; SHA256 matches20260908 copies exactly (rules fb2de1d46a2b5fdb5d8c879b9278d7eb1fd2103d28b87d428320d2ab07ce4355; contract6c1166856794f306cd32b7dca4a33a91f1690e3e9f5283471ff5e7074441f938). Parent verified wait advanced to7complete pairs10/14points, healthy pair terminations. No new engine modifications or archive. Continuation waiting for parent completion; no duplicate launch.

## Combined parent screen passed; replay underway
Parent session32785 completed exit0:29W10D11L=34/50points(68%), white74%black62%, no failed terminations. Independent final audit saved combined_parent_final_audit_01.json; all50PGNs/clocks/runtime/harness hashes verified. Development parent gate passed, not qualification. Continuation session20981 confirmed live and transitioned automatically to clock_replay_staged. Next combined replay then live50game development screen if timing/legality replay passes. No duplicate launches or runtime edits.

## Combined live development gate independently verified
Completed combined_live_12s_50g:43W2D5L=44/50points,88%score,86%actual wins,zero reliability failures. Independently replayed/audited all50games,25pairs,clocks and runtime/harness hashes; saved combined_live_final_audit_01.json. This passes development live60%score gate only. Session20981 confirmed live; driver advanced to screen_running_pvs. Latest PVS snapshot6games5W1D0L,healthy; partial only. Remaining RL,staged,LMR,aspir then full-clock development and new independent confirmation. No promotion or ZIP. White84%black92% in live report does not by itself establish absence of colour effects. No runtime changes or duplicate launches.
