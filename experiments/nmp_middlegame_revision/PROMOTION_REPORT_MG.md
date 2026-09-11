# NMP Pawn-Fix Promotion Report — SHIPPED UNQUALIFIED BY EXPLICIT USER ORDER

**Date:** 2026-09-10
**Candidate:** `experiments/search_v2_nmp_mg_01` (frozen NMP + pawn-attack edge-mask fix only)
**Artifact:** root `agent.zip` (this build)
**Status: UNQUALIFIED — packaged on direct user order before any game evidence.
The 50-game gate screen was 0-3 when packaging was ordered. Read this before uploading.**

## 1. What changed (verified)

Pawn-attack edge masks were transposed in both eval paths: `<<7`/`>>9` used
NOT_H (0x7F..) where NOT_A (0xFE..) belongs and vice versa, so a-file pawn
attacks wrapped onto the h-file as phantoms while real attacks went uncounted
(30/128 single-pawn maps wrong per path). Fix verified three ways
(bit-arithmetic derivation, python-chess convention, mapping suite:
256 checks + 480 kernel checks pass, 0 errors after fix). Isolation confirmed:
only `evaluation.py` + `fast_eval.py` (8 lines each) + manifest differ from NMP.
The fix feeds the king-safety attack term directly (flank-storm assessment).

## 2. What was NOT established before packaging

- The 50-game screen vs NMP (`mg_vs_nmp_50g`) stood at 0-3 (noise, not signal).
- No 60% gate pass, no audit, no silky comparison for this candidate.
- The R94 critical position now yields O-O-O at depth 5 (probe only, not strength).

## 3. Artifact verification (this ZIP)

- Built with unmodified `harness.package.build` from the frozen mg dir.
- 12 members, 79,564 bytes zipped / 180,483 unzipped (cap 50,000,000).
- Clean-extract hash comparison 12/12 vs frozen manifest.
- Both-colour smoke games from the extracted artifact: no problems.
- Previous root `agent.zip` (NMP `07EA0855…`) preserved as `agent_prev_nmp_20260910.zip`
  (hash-verified copy) — roll back by copying it back to `agent.zip`.
- Imports: chess/numba/numpy + first-party only; no subprocess/network/binaries.

## 4. Recommendation

Let the running screen finish. If mg clears 30/50 with zero failures, this ZIP
is retrospectively justified — keep it and proceed to silky comparison. If it
fails, roll back to `agent_prev_nmp_20260910.zip` and diagnose. Do not upload
an 0-3-candidate to rated play without reading this file.
