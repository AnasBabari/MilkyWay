# Project Astralix — implementation plan & continuation handoff (2026-09-06)

Codename **astralix** for the next enhanced MilkyWay competition engine.
Goal: a new flagship that scores **>=50% against Stockfish level 6, then
level 7**, in paired tournaments. Current status: **not achieved** — the
v1 candidate regresses and the harm is under diagnosis. Do not promote,
package for upload, or claim Elo gains. Nothing below authorizes an upload,
a production promotion, a remote tag rewrite, or new Codex tasks.

## 1. Repository and exact state

- Repo: `C:\Users\Babar\Documents\Coding\Projects\chess_bot\MilkyWay`
  (the parent `chess_bot` directory is not a Git repository).
- Branch: `main`, HEAD `834ceb8` (upstream sync merge, pushed to origin).
- Working tree (uncommitted, as found — do not lose):
  modified: `.gitignore`, `evaluation.py`, `search.py`,
  `tests/test_harness_rules.py`, `tests/test_package_determinism.py`,
  `training/data/download_pgn.py`;
  untracked: `artifacts/`, `baselines/stockfish/`,
  `docs/STOCKFISH_BENCHMARKS.md`, `experiments/astralix/`,
  `experiments/engine-v2/`, `experiments/r34/`,
  `tests/test_stockfish_integration.py`, `tools/benchmark_stockfish.py`,
  `tools/candidate_screen.py`, `tools/confirm_bank.py`,
  `tools/generate_level_bank.py`, `tools/measure_acpl.py`,
  `tools/prepare_r34_candidates.py`, `tools/prepare_r34_new_candidates.py`,
  `tools/prepare_speed_candidate.py`, `tools/replay_r34.py`,
  `tools/screen_bank.py`, `training/scripts/build_extended_dataset.py`
  plus training outputs (datasets, checkpoints, logs).
- Read `AGENTS.md`. In particular: do not edit `harness/`, never package
  Stockfish or any third-party engine/network, use `.venv/Scripts/python.exe`
  (Python 3.12) for repo work and `training/.venv/Scripts/python.exe`
  (torch 2.6 cu124, CUDA working on RTX 2060 6GB) for training work.
- Stockfish binaries (offline only): Temp universal build
  (`.../Temp/opencode/sf/stockfish/...universal.exe`, ~1.05M NPS bench)
  and the WinGet AVX2 build. `STOCKFISH_PATH` or `baselines/stockfish`
  discovery covers both.

## 2. What has been done (with evidence)

### 2.1 Standing baseline (earlier sessions, committed)

Classical engine MW-0.2: iterative-deepening PVS alpha-beta, TT, MVV-LVA /
killer / history ordering, quiescence, aspiration, LMR, null-move, futility,
proportional time manager with 0/320 probe overruns, 32/32 unit tests,
500/500 fuzz, 96.0% over 100 games vs MW-0.1. R34 report (rejected both
M19-A at 50.0% and KS-C at 52.5% for promotion). Frozen snapshots in
`versions/` (`mw_0_2`, `rc1_variants/*`, `experiments/r34/checkpoint`).

### 2.2 Upstream sync (done, pushed)

Fetched `advitrocks9/aichessathon-starter` through `aa6e586`, merged as
`834ceb8`, pushed to origin. Seven commits: 600-ply cap draws, bare-king
flag draws, third-occurrence (not potential) draws, container
suspend/resume with clock-annotated PGNs, 8-opening bank, seeded arena
with CIs, AST-based packaging with **two full-clock smoke games in
`make zip`**, Python `==3.12.*` pin. Resolutions: `agent.py` kept ours,
`harness/referee.py` taken upstream (subsumed our partial sync),
`README.md` kept ours plus sync-notes section, `AGENTS.md` took upstream
clock wording. Gates after merge: ruff clean; mypy clean except 4
pre-existing upstream Windows-only `SIGSTOP/killpg` notes in
`harness/sandbox.py` (upstream CI is Linux; left untouched per policy);
80/80 unit tests; 19/19 harness-rule tests (one updated for
clock-annotated PGNs). Consequence: pre-sync tournament numbers are not
directly comparable to post-sync ones (new draw rules + curated openings).

### 2.3 Rated-game recon (Downloads)

Latest downloads analyzed: **R44 loss vs imperialists** (Petroff start, we
White, mated move 61): greedy queen sorties (19.Qxb7, 23.Bxa7) losing
tempi, blind to the ...f5-f4-e3 pawn storm and queen infiltration,
**41.Rf3?? dropping the exchange to 41...Qxf3+**, passive lost-endgame
drift. Clock healthy (2.4 s avg, 17 s left) — a quality, not time, failure:
material greed, king-safety blindness, shallow tactics. R35 also on file.

### 2.4 Data expansion (done)

Pulled 8 more GM collections (Anand, Kramnik, Nakamura, Caruana, Topalov,
Aronian, Ding, Nepomniachtchi) via the extended
`training/data/download_pgn.py`. Corpus audit: **55,384 games, 12 players**,
~40% draws, avg 76–97 plies, Elo up to 2882 (full table in session notes;
well above the required 500 games). Built `training/datasets/master_value_v2`:
**72,002 balanced records** (61,758/6,718/3,526 train/val/test,
game-hash split, benchmark banks excluded, deduped): every phase, both
colours, all results — deliberately NOT winner-only.

### 2.5 The degenerate-value trap (found and documented)

The old 32k set sampled winner-moves from decisive games only, so every
value target was constant +1.0 (measured mean +1.000, std 0.000). A net
trained on it "converges" (val MSE ~0) while learning nothing — worse than
useless. Rule: value signal must come from search labels, never from
winner filtering. The v1 scalar pretrain on that set is retired for cause.

### 2.6 Labelling (done)

`training/scripts/label_value_dataset.py`: multi-worker full-strength
Stockfish, 50k nodes, MultiPV 4, 8 workers. Full v2 set labelled:
**100% policy/soft/value coverage**, value mean −0.058 std 0.217 (real
spread, balanced signs). Shards + per-split manifests under
`training/datasets/master_value_v2/{train,val,test}/`.

### 2.7 Pretraining rounds (RTX 2060, training venv)

Joint policy+value net (`training/models/flagship.py`): 18x8x8 input,
64ch x4 ResBlock trunk warm-started from `best_student.pt` (62 tensors),
policy head retained, value head fresh. Loss: hard CE + 0.5 KD from shard
soft targets + value term. Results:
- **v2 (WDL head, unweighted, LR 3e-4)** → `training/checkpoints/flagship_v2/`:
  policy top-1 **0.22 vs 0.15 shipped** on held-out masters, sane level
  values (±11 cp on level positions), underconfident tails, INVERTED
  extremes (white-up-queen → loss side). Exported 5.53 MB ONNX, parity
  1e-5/1e-6, **0.5 ms joint inference** on one CPU core.
- **v3** (decisive weight 1+3|v|): bipolar ±1200 saturation. Retired.
- **v4** (smoothing + mild weight + LR 1e-4): saturated all-loss outputs.
  Retired. (A mid-run duplicate-process scare was forensically resolved to
  a uv-shim parent/child pair — see §5.4 — but the weights stand retired
  on their measured merits regardless.)
- Standing lesson: tails need emphasis WITHOUT collapse; every future run
  gets queen/extreme probes during training, not after.

### 2.8 Astralix v1 variant (built, codename applied)

`experiments/astralix/v1/` (frozen candidate dir) = post-sync HEAD base,
plus: (1) depth-limit removal (`max_depth = 4 if time_left_ms < 1200 else
64`); (2) v2-WDL net as `weights/milkyway_astralix.onnx` with a
value-capable `root_policy.py` (single joint inference: policy scores +
WDL→cp conversion); (3) sensor-fusion blend (net trusted near level,
exact static counting past ~±450 cp); (4) uncertainty time scaling
(|value − last score| scales soft deadline within [0.9x, 1.35x], never
past hard). `experiments/astralix/v1_classical/` is the identical dir
minus weights (evaluator self-disables → classical ablation control).
Codename applied to: experiment dir, model file, variant default path,
`experiments/astralix/README.md`. Deliberately excluded: uncommitted
working-tree KS_C/qsearch experiments (separate attribution track).

### 2.9 Tournaments (the bad news, measured honestly)

Conditions unless noted: our 30 s + 0.3 s, Stockfish skill 6 (~0.3 s/move
from clock budgeting), paired colours, workers=1. Baseline and flagship
ran IDENTICAL pair IDs (perfectly paired comparison).

| Match | Score | ACPL (us) | Blunder% |
|---|---|---|---|
| Classical+depth (net OFF) vs SF6, 12 games | **+3 =3 −6, 37.5%** | 27.1 | 2.9 |
| Astralix v1 (net ON) vs SF6, 12 games | **+0 =2 −10, 8.3%** | 33.8 | 3.8 |
| v1 vs v1_classical head-to-head, 20 games 10 s+0.1 s | **+6 =4 −10, 40%**, CI 22.5–57.5%, Elo −70 [−215, +53] | — | — |

No failed terminations anywhere. Clock profiles sane in both SF6 runs
(early ~23/21 s, mid ~11/8 s, late ~5 s left) — not a time scramble.
Per-pair (same 6 positions): baseline 0/0/1/0.5/1.5/1.5 = 4.5; flagship
0/0.5/0/0/0/0.5 = 1.0. The net as currently integrated HURTS (weakly
proven head-to-head, strongly suggested vs SF6); the 12-game samples are
small and this is not yet isolated to policy-ordering vs value-scaling.

## 3. What remains (ordered)

**R1. Isolate the harm (ablation part 2).** Build a policy-only variant
(ordering ON, value scaling OFF — needs a small engine toggle; env-gated
like `MILKYWAY_ROOT_POLICY` is acceptable in-variant) and run v1-full vs
policy-only vs classical, 10 pairs fast TC each. This decides whether the
retrained policy head or the value/time path is the poison. Do not skip
to retraining blind.

**R2. Fix the identified component.**
- If policy ordering: compare tail-ranking quality (top-5/10 agreement vs
  shipped net on tactics; order_root_moves contribution audit). Candidate
  fixes: distill ordering from the shipped net (freeze trunk, train head
  only), or cap policy influence below captures/history (already capped —
  verify effective weights empirically).
- If value scaling: tighten bounds (e.g. [0.95x, 1.15x]), gate scaling on
  |static| < 300, or drop scaling and keep value for telemetry only.
- Re-run the losing ablation to confirm the fix before any SF6 return.

**R3. Retrain the value head properly (v5).** Single writer (verify via
ParentProcessId, never kill shim children). Config: v2 loss + mild
decisive weight (1+|v|) + smoothing + LR 1e-4, patience ≥10. Gate DURING
training: queen/bare-board/natural-decisive probes every 5 epochs; abort
on saturation or inversion. Success bar before export: correct SIGNS on
all extreme probes and natural-decisive errors within ~2x of level MAE.

**R4. Astralix v2 integration + SF6/SF7 campaign.** Same conditions as §2.9
for comparability. Predeclared gates: below 45% at 12 games stop and
diagnose; 45–55% extend to 100 paired games; promote-to-next-stage only at
≥55% with lower CI above 50%. Then level 7, then MW-0.2 regression check
(`paired_arena.py` vs `versions/mw_0_2`), then medium/full-clock scaling.

**R5. Honest promotion track.** Only for a variant clearing R4: full ruff +
strict mypy + unit suite + harness-rule tests + rated regressions +
time-probe + fuzz + ONNX/load/latency checks + deterministic double-build
packaging + Python 3.12 harness smoke games both colours + consolidated
REPORT.md. No upload without explicit user authorization.

**R6. M16 classical tuning** stays queued behind a working net; do not
tune eval and search simultaneously with net changes (causal attribution).

## 4. Standing rules (unchanged)

- Stockfish is offline sparring/oracle/labeler ONLY. Never in `agent.zip`,
  never invoked by the agent, never `--include`d by the packager. Runtime
  deliverable stays 100% independent (checked: `make zip` output lists).
- Do not edit `harness/`. Do not retrain + reintegrate + retest in one
  blind jump; one mechanism per variant, frozen hashes, arena decides.
- A 40–55%-over-small-N result is encouragement or noise, never proof.
  Promotion needs substantial samples, lower CI above 50%, independent
  confirmation, zero reliability failures, no MW-0.2 regression, no
  longer-clock reversal.
- Conserve usage: bounded local scripts, batch verification, no subagents.

## 5. Operational lessons (paid for — reuse them)

1. **uv-shim PIDs**: `.venv\Scripts\python.exe` re-execs the real
   interpreter → WMI/tasklist shows TWO pythons per logical process.
   Always check ParentProcessId chains before killing anything.
2. **Phantom filesystem errors**: isolated "not found" / empty reads that
   contradict `cmd /c dir` — retry via `cmd /c dir` and tasklist, do not
   act on a single provider glitch (never delete "missing" ejected evidence
   without cmd-level confirmation).
3. **Single writer per out dir**, verified via parent chains; out dirs with
   clashes get wiped and restarted (they contain no completed games).
4. **Launch pattern that works**: absolute-path `.cmd` file + WMI
   `Win32_Process.Create`; `Start-Process` hangs in this environment.
5. **Temp-file scripts** for any non-trivial quoting (never fight nested
   PowerShell quotes inline); repo root must stay free of `*_tmp.py`,
   result `.txt` files (cleaned this session).
6. **CKPT provenance**: concurrent writers to one checkpoint path corrupt
   silently — one writer, PID-verified, per training run.

## 6. Exact commands appendix

```powershell
# value-tail sanity probes during/after any training run
training/.venv/Scripts/python.exe training/scripts/export_flagship.py --checkpoint training/checkpoints/flagship_vX/best_flagship.pt --output training/checkpoints/flagship_vX/milkyway_astralix.onnx
# baseline (classical) and flagship SF6 screens (sequential, workers=1)
.venv/Scripts/python.exe tools/benchmark_stockfish.py --agent experiments/astralix/v1_classical --level 6 --pairs 6 --base-ms 30000 --increment-ms 300 --workers 1 --out experiments/astralix/sf6_baseline
.venv/Scripts/python.exe tools/benchmark_stockfish.py --agent experiments/astralix/v1 --level 6 --pairs 6 --base-ms 30000 --increment-ms 300 --workers 1 --out experiments/astralix/sf6_flagship
# net ablation (fast TC screen)
.venv/Scripts/python.exe tools/candidate_screen.py --agent experiments/astralix/v1 --opponent experiments/astralix/v1_classical --out experiments/astralix/net_ablation --pairs 10
# gates (repo root)
uv run ruff check . ; uv run mypy 2>&1 | Select-Object -Last 3
uv run python -m unittest discover -s tests 2>&1 | Select-Object -Last 4
```

## 7. Session log (2026-09-07 unless noted)

- **R1 verdict** (`r1_policy_vs_control`, policy-only vs classical, 20 games
  fast TC): **+11 =2 −7, 60%, CI 42.5–77.5%**, colour-symmetric 75/41 split
  noted, no failures. Policy ordering is neutral-to-positive (+70 Elo point
  estimate) — NOT the SF6 collapse cause. R1 arms verified hash-frozen via
  `r1_manifest.json`; value/scaling provably off in both arms.
- **Converter bug found and fixed**: the runtime fed raw WDL logits as
  probabilities (startpos read −1199.8 cp; correct softmax-first value
  −17.9 cp). This corrupted the blend and randomized time scaling in every
  net-enabled run — prime suspect for the 8.3% SF6 collapse. Fixed in
  `experiments/astralix/v1/root_policy.py` (stable softmax + comment);
  the 8.3% result is therefore INVALID as a measure of the intended
  design and must be re-run, not cited.
- **Checkpoint forensics corrected**: v3/v4 "bipolar" ONNX-probe readings
  used the same missing-softmax bug and are void. Re-probed with correct
  math: v2-WDL sane levels/inverted bare-board extremes; v3 genuinely
  worse; v4 best levels (+2 startpos). v3 retirement stands; v4
  rehabilitated as a spare (single-writer doubt noted but its readings are
  now the best observed — keep, do not use without a clean retrain).
- **Duplicate-process doctrine**: `.venv` python is a uv shim — WMI shows
  shim + real interpreter per logical process. Always verify
  ParentProcessId chains before killing anything.
- Next: re-run SF6 flagship (fixed converter) in a FRESH out dir
  (`sf6_flagship_fix1`), same pairs/seed for direct comparability with the
  37.5% classical baseline, then level 7 per R4 gates.
- **fix1 result** (`sf6_flagship_fix1`, same 6 pair IDs): **+3 =1 −8,
  29.2%** (buggy run was 8.3%). Converter fix recovered most of the
  collapse but flagship still trails classical 37.5% on identical
  positions. Since R1 exonerated policy ordering (+70 Elo point est.),
  the remaining suspect is value blend / uncertainty time scaling.
  Next datum in flight: frozen `r1_policy` arm (policy ON, scaling OFF)
  vs SF6, same conditions, fresh out dir (`sf6_policyonly`). If
  policy-only >= baseline, scaling is confirmed poison → drop/tighten it
  and re-run; the projection for policy+depth without scaling is then
  ~baseline+70 Elo, back in striking distance of 50%.

## 8. Session log, continued (2026-09-07)

- **R1 verdict**: policy-only vs classical, 20 games: **+11 =2 −7, 60%,
  CI 42.5–77.5%** (+70 Elo point est.). Policy ordering exonerated.
- **Converter bug fixed in variant** (`v1/root_policy.py`): raw WDL logits
  were fed as probabilities (startpos read −1199.8 cp; correct −17.9 cp).
  This randomized blend + time scaling in every net-enabled run — prime
  suspect for the SF6 collapse, now removed as a confound.
- **Checkpoint forensics, corrected**: v3/v4 "bipolar" ONNX readings used
  the same missing-softmax bug and are VOID. Re-probed correctly: v2-WDL
  sane levels/inverted bare-board extremes; v3 genuinely worse (retire
  stands); v4 best levels (+2 startpos) — rehabilitated as spare, unused
  for now. Dim order [WIN, DRAW, LOSS] proven on 20 natural decisive
  positions (dim0 tracks stm-wins 0.42 vs 0.23).
- **fix1 re-run** (converter fixed, same 6 pairs): **+3 =1 −8, 29.2%**
  (buggy run 8.3%, classical baseline 37.5%). Fix recovered most of the
  collapse; residue trails baseline.
- **Policy-only vs SF6** (frozen `r1_policy` arm, same pairs):
  **+3 =4 −5, 41.7%** — beats classical baseline. By elimination across
  shared-everything arms, **uncertainty time scaling is the poison**
  (overspend early on noisy disagreements → 28% poorer mid-game clock →
  late blunders). Mechanism coherent with clock profiles and blunder
  timing; effect size (~−100 Elo) warrants removal, not tuning.
- **Scaling deleted** from `v1/engine.py` (+ dead `_last_score`/blend/
  `math`/`evaluate` refs); policy ordering + depth delta retained.
  Variant smoke: 3/3 legal, healthy times. Current standing estimate for
  astralix v1 (policy+depth): **41.7% vs SF6** — to be re-measured in the
  level-7 campaign, not asserted from a different arm's games.
- **No agent.zip generated**: the plan conditions it on a qualified
  candidate; none exists. The stale `artifacts/agent-tested-*.zip` is a
  pre-astralix classical build, NOT the flagship — do not upload it as one.

## 9. Session log, v2 crash (2026-09-07)

- **v2 (LMR-check exclusion) crashed 12/12 vs SF6** (all by engine crash,
  plus pathological Ra2/Ra1 shuffling pre-crash). Root cause, fully traced:
  `board.gives_check(move)` pushes internally and asserts pseudo-legality;
  on an illegal input the push raises BEFORE state is saved while its
  `finally: pop()` still runs, stealing the caller's pushed move. Each
  theft permanently desyncs board/stack (later pops restore wrong states),
  producing garbage search then an illegal-move crash. Instrumentation
  proved: exactly one net push/pop imbalance class, LIFO-identified leaked
  move, illegal gives_check input with caller-frame forensics, and
  `push()` source showing the assert fires after stack/counter mutation.
- **Fix applied**: LMR gives_check line reverted (v2 search diff vs v1 is
  now comment-only); all `gives_check` calls guarded by
  `is_pseudo_legal` first (cheap, push/pop-free). Crash-FEN repro now
  returns legal f1f3 in 0.6 s. Tactics + SF6 re-run still required before
  any claim. The LMR-check IDEA survives; only this implementation died —
  any retry must use a push/pop-free check test.
- **No agent.zip**: none of v1 (41.7% est.), v2, or root clears the 45%
  bar. Packaging now would launder an experiment into a contender.

## 10. Session log, LMR-check crash + guarded retry (2026-09-07)

- **v2 (unguarded LMR-check exclusion) crashed 12/12 vs SF6**, all engine
  crashes after pathological Ra2/Ra1 shuffling. Forensics chain (all
  reproduced locally on the crash FEN): `gives_check()` pushes internally
  and asserts pseudo-legality; on an illegal input the push raises BEFORE
  saving state while `finally: pop()` still runs, stealing the caller's
  pushed move. Each theft desyncs board/stack (later pops restore wrong
  states) → garbage search → illegal-move crash at final push.
  Provenance of the first illegal input remains a residual unknown, but the
  theft primitive + crash chain are fully characterized; the line is guilty
  by clean delta (v1 crash-free over 1000+ games, 4-line diff).
- **Fix**: LMR line reverted; every `gives_check` call site guarded by
  `is_pseudo_legal` first (pure bit ops, makes theft unreachable).
  Crash-FEN repro now returns legal f1f3 in 0.6 s; mate-in-1 intact;
  400-position fuzz clean; ruff clean.
- **Guarded retry tournament** (`sf6_v2guarded`, same 6 pairs):
  **+1 =4 −7, 25%**, zero failures. Below the 41.7% policy-only reference
  (gap within noise at n=12, but direction + node cost argue against).
  LMR-check exclusion SHELVED as a strength lever; idea needs a
  push/pop-free check test to return.
- **Key structural insight for the campaign**: SF movetime is capped at
  1.0 s/move for any healthy clock, so longer OUR clocks are free Elo.
  Running frozen `r1_policy` (policy-only, 41.7% @30 s) vs SF6 at
  **120 s + 0.5 s** (`sf6_r1policy_120s`, same pairs) — the highest-EV
  route to the 45% bar. No agent.zip: still no qualified candidate.

## 11. Session log, 45% push (2026-09-07)

- Extension (fresh seed-7 positions): **+1 =4 −7, 25%**. Combined 24:
  **10.5/24 = 43.75%** — one game-point short of 45%. No bank colour skew
  (White won 42%/50%); losses concentrate mid-game (CPL 37) and late,
  set B played out sharper/faster than set A.
- Third set running: same engine/TC/opponent, seed 99, 6 fresh pairs
  (`sf6_r1policy_120s_ext2`, ~35 min). Combined-36 verdict decides: ≥45%
  → head-to-head vs live for promotion, then gates + agent.zip.
- **Third set: +3 =2 −7, 33.3%. Combined 36: 14.5/36 = 40.3% — bar
  MISSED.** Per-set: 62.5 / 25.0 / 33.3 (SE ~14% each — expected spread,
  not engine changes). White-pieces wins by set: 42/50/67%.
  Within white-favoring set 3, SF defended black far better (2.5/6) than
  we did (0.5/6): real defensive-technique gap joins the known mid-game
  CPL bleed as diagnosed causes. No promotion, no package. Next: strength
  work first (M16 tuning, safe LMR variant, proper value integration) —
  more games alone is variance-hunting at n=36.

## 12. Session log, full-clock breakthrough (2026-09-07)

- **Policy-only (frozen `r1_policy` arm) vs SF6 at 120 s + 0.5 s, same
  pairs: +6 =3 −3, 62.5%** (white 66.7%, black 58.3%), zero failures.
  Full-clock depth confirmed as the highest-EV lever: 41.7% @30 s →
  62.5% @120 s with SF capped at 1 s/move throughout.
- **45% bar: MET on point estimate (n=12, Wilson CI ~35–84%).**
  Confirmation extension running: 6 fresh pairs (seed 7, different
  positions), same TC/opponent, `sf6_r1policy_120s_ext`. Promote + package
  only if the combined 24-game sample stays ≥50% with no failures and no
  MW-0.2 regression (paired_arena check still owed before any promotion).

## 12. Session log, best-vs-live 100 games (2026-09-07)

- **r1_policy (best candidate) vs live `live_e7583f0`, 100 games paired,
  10 s + 0.1 s: +41 =16 −43, 49.0%, CI 39.5–58.5%, Elo −7 [−74, +60].**
  White 47% / Black 51% (no skew). 84 checkmates, 9 threefolds, 3
  insufficient-material, 4 fifty-move; zero failures. Integrity: 50 unique
  pair IDs, recompute matches exactly.
- **Verdict: statistically even — NOT better than live.** The 20-game
  37.5% v1-vs-live wobble does not replicate at n=100. Combined with
  40.3%/36 vs SF6, no candidate clears any bar: no promotion, no new
  package. The live build (agent.zip `3e2ba178e3adb7fa`) remains champion
  by default. Next strength work unchanged: M16 tuning, safe LMR-check,
  proper value integration.

## 13. Session log, championship + quick zip (2026-09-07)

- **Championship** (v1-trimmed vs live `live_e7583f0`, 20 games fast TC):
  **+7 =1 −12, 37.5%** — v1 LOSES to live clearly, no failures either
  side. The working-tree KS_C default + qsearch tweak are doing real work
  in the full configuration; R34's isolated-variant rejection does not
  transfer. Standing order: live (root working tree) > v1-trimmed.
- **agent.zip rebuilt from root** (post-sync packager): 4,881,616 bytes,
  5,354,418 unzipped, 11 entries (10 modules + shipped policy net), zero
  banned content, smoke games pass as both colours (English/French Winawer
  openings, ply-cap finishes). sha256 `3e2ba178e3adb7fa`. This is a FRESH
  BUILD of the live configuration, not a promotion — astralix work (value
  reintegration, LMR-check safe variant, M16) resumes afterward. No upload.

## 14. Session log, M16 on 72k labels: fit rejected (2026-09-07)

- Built `training/datasets/tuning_master_value_v2.npz` (61,758/6,718/3,526
  rows, 50 white-perspective features, y = white-perspective SF cp
  recovered exactly from tanh labels; 0 skipped). Reconstruction fidelity
  ±1 cp confirmed on samples.
- Huber fit (same methodology as M16-huber-01): val MAE 119.24 → 108.54
  (−10.7). **REJECTED anyway**: a dozen parameters pinned at sanity-bound
  floors (all material −17..−40%, mobilities = 1, bishop pair MG = 0),
  passed-pawn bonuses NON-MONOTONIC by rank (r2=1, r3=0, r4=0, r5=1,
  r6=37, r7=20), king safety gutted. The fit flattened outputs toward the
  label mean to harvest MAE on tactically noisy positions (static eval
  cannot match SF there by construction) — chess knowledge destroyed, not
  improved. No arena run: methodology rejects degenerate fits before
  burning games. Spot-check confirmed our eval is sane where it matters
  (SF200k says +1045 on the probed +924 position — no eval bug).
- Standing conclusion: linear coefficient tuning has hit its ceiling on
  sharp data (M16-huber-01's 53%/100 remains the best tuned result and it
  failed its gate). The mid-game gap is STRUCTURAL (static blindness to
  tactics): next levers are SEARCH-side (safe LMR-check, speed for depth,
  better value integration), in that order.

## 15. Session log, big-data push (2026-09-07)

- Pulled HuggingFace `adamkarvonen/chess_games` (direct HTTPS; the
  `huggingface_hub` lib 401s in this env): `lichess_200k_elo_bins`
  (~1 GB zip, 2.6 GB CSV, **5.95M rows**) + `lichess_100mb`.
- Analyzed: Elo bins 600–3200; stratified-sampled **7,102 games ≥2000
  Elo** (700/bin + all 2700+) → `training/data/raw_pgn/Lichess200k.pgn`.
  Corpus: 55,384 GM + 7,102 lichess = **62,486 games**.
- `build_value_dataset.py` gained `--sources`; built 70k v3 records.
  SF multipv4 labelling running (~40 min).
- Next: merge v2+v3 shards (~142k), fresh v5 pretrain (single writer,
  in-training extreme probes), integrate, tournament vs previous
  candidate (live) toward the 70% bar.

## 12. Copy-paste continuation prompt

Continue Project Astralix in
`C:\Users\Babar\Documents\Coding\Projects\chess_bot\MilkyWay`
(branch `main`, HEAD `834ceb8`). First read `AGENTS.md` and
`experiments/astralix/IMPLEMENTATION_PLAN.md` (this file). Treat it as
verified state, not authority to invent results. The goal is a flagship
scoring >=50% vs Stockfish level 6 then 7; current v1 REGRESSES (8.3% vs
SF6, 40% head-to-head vs its own classical control) and must be diagnosed
before any retraining or promotion. Do the local work; never upload,
promote, or ship Stockfish in any form. Conserve usage: bounded scripts,
batched checks, no subagents.

## 16. Session log, speed campaign (2026-09-07) — MEASURED GAIN

Frozen opponent for everything below: `experiments/live_e7583f0` (the previous
candidate). It is byte-identical to the live tree except `evaluation.py` and
`search.py`, so every match here is a single-variable A/B against our own
champion.

### Diagnosis first (do not skip this again)
Profiling one search (`scratch/prof_search.py`) showed the bottleneck was NOT
the network and NOT the eval coefficients: **evaluation 42%, python-chess
movegen/push ~30%**. Baseline throughput **13.3k NPS, depth 6** in ~4 s. The
mid-game gap called "structural" in §14 is, at this engine's level, mostly a
**throughput** problem — depth, not knowledge.

### Changes
1. **`fast_eval.py` (new)**: faithful njit port of
   `evaluation.evaluate_white_relative` to raw bitboards. Parity verified
   **0 mismatches / 2000 random positions** (`scratch/parity_fast_eval.py`).
   Eval 78 us -> 16 us. Wired in via `evaluation.warm_fast_eval()`; 5.6 s warm-up
   against a 90 s init budget; kill switch `MILKYWAY_FAST_EVAL=0`; falls back to
   the reference path on any exception so a numba problem can never lose a game.
2. **`search.py` quiescence cuts**: repetition scan gated on
   `halfmove_clock >= 4` (a repeat needs four reversible plies, and captures
   reset the clock), insufficient-material short-circuited by a bitboard test
   (any pawn/rook/queen => mating material), child transposition key computed
   only when `halfmove_clock >= 3`.
3. **Data**: `training/scripts/sample_lichess_big.py` gained `--cap-scale` /
   `--rate-scale`; pulled **220,000 lichess games** (>=2000 Elo, stratified) to
   `training/data/raw_pgn/LichessMega.pgn` (150 MB). Corpus ~275k games.

### Result
`experiments/speed_v1`, 20 pairs / 40 games, 10 s + 0.1 s:
**62.5% (+22 =6 -12), +89 Elo, 95% CI [47.5%, 77.5%]**, colour-symmetric
(62.5% white / 62.5% black), **zero failed terminations**. NPS 13.3k -> 26.7k,
depth 6 -> 7 at equal wall time. 85/85 unit tests pass.

Rule of thumb this establishes: **~2x NPS ~= +89 Elo** for this engine. The
70% bar therefore needs roughly another +60-80 Elo, i.e. another ~1.6-2x.

### Next lever, in priority order
- **python-chess movegen** is now the remainder (~33% generate_legal_moves,
  ~14% push, ~10% ordering). A numba legal-movegen kernel is the highest-EV
  remaining item; port `generate_legal_moves` / `_generate_evasions` /
  `_is_safe` / `_slider_blockers` from the installed python-chess and validate
  with **perft against python-chess** before wiring it in. An illegal move here
  corrupts the board silently (python-chess `push` does not validate), so perft
  parity is mandatory, not optional.
- Time management is very conservative: `time_left/40 + 0.7*inc` converges to
  spending only the increment while banking ~7 s. Knobs are now env-tunable for
  local experiments, but note **the harness refuses to run agents with
  `MILKYWAY_*` env overrides** ("Remove engine environment overrides first"), so
  A/Bs must change the code default, not the environment.

### Still not done
No fresh GPU pretrain ran this session (the v4 500k-position set is built but
unlabelled; policy needs no labels, value does). No `agent.zip` was produced:
none of this is packaged or uploaded, and §4's rules still apply.
