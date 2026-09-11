# NMP Promotion Report — development gate pass, UNCONFIRMED at full clock

**Date:** 2026-09-10
**Candidate:** `experiments/search_v2_nmp_01` (frozen combined + null-move pruning only)
**Artifact:** root `agent.zip` (this build)
**Status: development-qualified (60% gate passed). Full independent confirmation remains incomplete — no upload.**

## 1. Why NMP, and why the previous attempt failed

- The R94 king-safety candidate fixed its target blunder (+410cp oracle) but lost its screen 28/50: its queen-presence-gated central-king penalty taxed quiet positions and queen endings alike (no phase gate, no attack detection). 6 of 11 changed suite decisions were worse by the other session's own oracle. Rejected for cause; finisher declined correctly; no stray ZIP was produced.
- Search inventory showed combined's Numba search had TT + LMR/PVS + killers/history but **no null-move pruning** (MW-0.2 had it; the compiled rewrite dropped it). NMP was the largest verified-absent classical lever.
- A mirror-asymmetry lead in the baseline eval was measured and closed as cold (0.48cp mean, 8cp max over 269 positions).

## 2. The change (only `combined_search.py` differs from frozen combined)

Conservative NMP: depth >= 3, not in check, previous move real, static >= beta,
side owns a non-pawn piece (zugzwang guard), beta below mate bound; R=2 (R=3 at
depth >= 6); null window; fail-hard beta cutoff; pass = flipped side, cleared EP,
ticked halfmove, no history update. Deterministic builder:
`experiments/nmp_revision/build_nmp_candidate.py`. Ruff clean (candidate + scripts).

## 3. Verification (before any games)

- 240/240 suite positions legal; warmup ~18.5s (within 90s import budget).
- Fixed-depth-5 node ratio 0.80 mean / 1.00 max (pruning engages, never costs).
- Depth at fixed 2s: +1 to +2 on all 5 probes (9→11, 10→12, 7→8, 9→10, 8→9).
- 10/10 pawn-only endings + 5/5 tactical spots agree with combined (no zugzwang damage).
- 60 low-clock calls legal, max 0.266s. Evidence: `nmp_verification_01.json`.

## 4. Head-to-head vs frozen combined (the gate)

50 games, 25 pairs, 12s+0.1s, 3 workers, screen bank seed 20260906:
**+25 =12 −13 → 31.0/50 = 0.620** (gate 0.60), zero failed terminations,
colour-symmetric (+13=4−8 / +12=8−5), 25 complete pairs, runtime hashes match.
Bootstrap 95% CI [0.50, 0.74], Elo +85 [−0, +182] — a thin but predeclared pass.

## 5. Artifact verification (this ZIP)

- Built with unmodified `harness.package.build` from the frozen NMP dir.
- 12 members, 79,564 bytes zipped / 180,483 unzipped (cap 50,000,000).
- Clean-extract hash comparison 12/12 vs frozen manifest; both-colour smoke games pass.
- Previous root `agent.zip` (11:41 repackaging) preserved as `agent_prev_20260910_1141.zip`.
- Imports: chess/numba/numpy + first-party only; no subprocess/network/multiprocessing/file-IO.

## 6. Explicit gaps

- No full-clock confirmation for NMP (bank_03 + fresh 100-game run still required).
- Challenger bootstrap gates and the 60%-over-100 live gate are untouched by this change.
- Host sleeps nightly: disable sleep before any overnight run.
