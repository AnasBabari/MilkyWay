# TM-Ceiling Promotion Report — ZERO-GAME BASIS, TRIAL RUNNING

**Date:** 2026-09-11
**Candidate:** `experiments/search_v2_tm_01` (NMP + healthy-clock caps 3.5s->6s soft, 6.5s->12s hard)
**Artifact:** root `agent.zip` (this build)
**Status: installed on explicit user order with no game evidence. A full-clock
efficacy trial is running as retrospective validation. No upload.**

## 1. Basis (all that exists)

- Rated-clock analysis: slowest move pegs the 6.5s hard cap in every rated game
  with 20-100s remaining; habitual ~3s spending is divisor-set, so only starved
  critical moves change.
- 12s-identical-moves guard: 5/5 same moves at 12s TC (patched branch provably
  unreachable there) + suite legality + low-clock safety.
- Middlegame time probe: 2/46 corpus blunders convert at 3x time (thin signal).
- NO screens, NO gate pass for this candidate. The 20-game full-clock trial
  (`tm_fullclock_20g`, identical 10 pairs combined scored 10.0/20 on) will
  adjudicate: >=12.5 suggests gain, <=8.5 suggests harm.

## 2. Artifact verification (this ZIP)

- Built with unmodified `harness.package.build` from the frozen candidate dir.
- 12 members, 79,562 bytes zipped / 180,484 unzipped (cap 50,000,000).
- Clean-extract hash comparison 12/12 vs frozen manifest.
- Both-colour smoke games from the extracted artifact: no problems.
  (Smoke ran concurrent with the trial's first game; trial games checked clean after.)
- Previous root `agent.zip` (mg+delta `77FE6F29…`) preserved as
  `agent_prev_mgdelta_20260911.zip` — roll back by copying it back.
- Imports: chess/numba/numpy + first-party only; no subprocess/network/binaries.

## 3. Recommendation

Let the trial finish (~17:30, inside the daylight window). If it reads >=12.5,
plan a larger full-clock sample. If <=8.5, roll back to NMP or mg+delta and
revert the caps. Do not upload rated games on zero-evidence builds.
