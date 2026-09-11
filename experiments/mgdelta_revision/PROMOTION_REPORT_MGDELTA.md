# mg+delta Promotion Report — SHORT-SCREEN BASIS, UNCONFIRMED

**Date:** 2026-09-10
**Candidate:** `experiments/search_v2_mg_delta_01` (NMP + pawn-mask fix + quiescence delta pruning)
**Artifact:** root `agent.zip` (this build)
**Status: installed on 20-game short-screen evidence (12.0/20) by explicit user order.
No 50g, no full-clock confirmation. No upload.**

## Evidence

- 20-game screen vs mg: +11 =2 −7 → 12.0/20 (0.60), zero failures, colour-symmetric.
  Predeclared 60% gate met exactly. Wide CI ([0.36, 0.81]) stated, not hidden.
- Components already proven: pawn-mask mapping suite (256+480 checks), delta
  pruning node savings, full legality suites, low-clock safety.
- 50g confirmation screen was waived by the user for time; a 50g run
  (`mgdelta_vs_mg_50g`) was launched and left running as retrospective evidence.

## Artifact verification (this ZIP)

- Built with unmodified `harness.package.build` from the frozen candidate dir.
- 12 members, 79,920 bytes zipped / 181,749 unzipped (cap 50,000,000).
- Clean-extract hash comparison 12/12 vs frozen manifest.
- Both-colour smoke games from the extracted artifact: no problems.
- Previous root `agent.zip` (NMP `07EA0855…`) preserved as
  `agent_prev_nmp_20260910.zip` — roll back by copying it back to `agent.zip`.
- Imports: chess/numba/numpy + first-party only; no subprocess/network/binaries.

## Strength reading (honest)

- Relative: NMP-class, roughly +400 ± 200 over silky at 12s (transitive chain,
  not a measurement). Full-clock strength unmeasured for this build.
- Absolute: no anchored number exists; SF7-anchored guesswork puts the lineage
  in the low-2200s Lichess-equivalent at full clock, ±150 per link.
