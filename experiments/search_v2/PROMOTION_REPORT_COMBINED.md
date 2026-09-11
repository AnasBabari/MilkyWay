# Combined Promotion Report — BEST-AVAILABLE, UNCONFIRMED

**Date:** 2026-09-10
**Candidate:** `experiments/search_v2_combined_01` (staged quiescence generation + LMR, frozen)
**Artifact:** root `agent.zip` (built 2026-09-10 from the frozen runtime, see recipe below)
**Status: UNCONFIRMED — shipped by explicit user override, NOT by passing the 100-game confirmation gate.**

## 1. Why this ZIP exists despite no confirmation

The 100-game live confirmation (`confirm_combined_live_120s_100g`) was disqualified by a host-OS sleep/wake artifact (opponent flag across an overnight suspend; see `reliability_disqualification.json`), not by candidate behavior. The user explicitly authorized packaging the best-available candidate on existing evidence, overriding the confirmation gate. No upload is authorized by anything here.

## 2. Evidence for combined (all audited, frozen runtime untouched throughout)

| Test | Result | Evidence |
|---|---|---|
| Parent screen, 12s, 50 games | 29W 10D 11L, 0.680 | `combined_parent_12s_50g`, final audit passed |
| Live silky screen, 12s, 50 games | 43W 2D 5L, 0.880 | `combined_live_12s_50g`, final audit passed |
| PVS challenger, 12s, 50 games | 38W 6D 6L, 0.820 | `combined_pvs_12s_50g` |
| RL challenger, 12s, 50 games | 33W 6D 11L, 0.720 | `combined_rl_12s_50g` |
| Staged challenger, 12s, 50 games | 25W 13D 12L, 0.630 | `combined_staged_12s_50g` |
| LMR challenger, 12s, 50 games | 29W 7D 14L, 0.650 | `combined_lmr_12s_50g` |
| Aspiration challenger, 12s, 50 games | 34W 7D 9L, 0.750 | `combined_aspir_12s_50g` |
| Astralix v1 sideline, 12s, 20 games | 19W 1D 0L, 0.975 | `combined_astralix_12s_20g`, audited |
| Live silky pooled full-clock (20 predeclared + 30 extension) | 25W 7D 16L, 0.594 over 48 scored | `combined_live_120s_20g`; meets the user's 55% bar (27.5); 1 void + 1 sleep-flag excluded |
| Full-clock reliability | 0 genuine failures in 68 combined full-clock games | no flags/crashes/illegals by either side in play |
| Live confirmation, 100-game | DISQUALIFIED (sleep artifact), 13.0/22 at stop | `confirm_combined_live_120s_100g/reliability_disqualification.json` |

Zero reliability failures attributable to the candidate in 400+ recorded games across all screens.

## 3. What was NOT done (explicit gaps)

- 100-game independent confirmation (bank_02 generated, audited, frozen — then partially exposed by the disqualified run; bank_03 required for any future attempt).
- Challenger bootstrap gates at full clock.
- Any retraining, tuning, or mechanism change since freezing (none — by design).

## 4. Artifact verification (this ZIP)

- Built with the UNMODIFIED `harness.package.build` from `experiments/search_v2_combined_01`, includes `("weights",)`.
- 12 members, 79,062 bytes zipped / 178,701 unzipped (cap 50,000,000).
- Clean-extract hash comparison: 12/12 match the frozen manifest.
- `harness.package.smoke` from the extracted artifact, both colours vs house: no problems.
- Previous root `agent.zip` preserved as `agent_prev_root_20260907.zip` (hash-verified copy).
- Imports: chess, numba, numpy + first-party only. No subprocess/network/multiprocessing/file-IO in runtime. No third-party engine code, binaries, or published networks.
- Ruff clean on all runtime files.

## 5. Known deviations (recorded, not hidden)

- `mypy --strict` reports 28 errors in the frozen runtime (untyped defs, missing type args, export-visibility nits). Frozen-evidence immutability outranks style: the files were NOT edited to chase the linter because that would ship untested code. Behavior is verified by the game record above.
- Timings vary under host load; no speed claims beyond the audited screens.
- Host sleeps nightly (~23:5x, Application API): any future overnight run requires sleep disabled first, or evidence will be corrupted again.

## 6. Provenance

- All code team-written (compiled search core, staged generation, LMR block); value weights `weights/compact_value.npz` from the team's own outcome-training pipeline (offline Stockfish labels only — the normal, allowed route).
- Frozen manifest: `experiments/search_v2_combined_01/manifest.json`; combined_search.py SHA256 c9e4806ff7eac071e1bbe43c8f5dffe7ff63c1a94a973dbbf9c5e89e052a779f.
- Reproducible recipe: `harness.package.build(<frozen dir>, <out>, ("weights",))` — member order deterministic; file mtimes vary.
