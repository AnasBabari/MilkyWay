# NMP candidate: design and verification plan

Isolated variant `experiments/search_v2_nmp_01`: byte-copy of frozen
`search_v2_combined_01` plus ONLY null-move pruning in `combined_search.py`
(builder: `experiments/nmp_revision/build_nmp_candidate.py`, deterministic).

## Guards (conservative)

- depth >= 3, not in check, previous move real (`null_ok` flag).
- Static eval >= beta (one extra eval per candidate node).
- Side to move owns a non-pawn piece (zugzwang guard).
- `beta < MATE - LIMIT` (never prune a mating search).
- R = 2 (R = 3 at depth >= 6); null window; fail-hard beta cutoff.
- Pass = flipped side, cleared EP, ticked halfmove; no history update
  (accepted standard risk, documented in code).

## Why this is the breakthrough bet

Combined's search has TT + LMR/PVS + killers/history but no NMP
(MW-0.2 had it; the compiled rewrite dropped it). NMP is the largest
verified-absent classical lever: expected +1 ply and large tactical gains.

## Verification (verify_nmp.py)

Legality on 240 suite positions; fixed-depth-5 node ratio (must drop);
depth-at-2s (must not regress); 10 pawn-only endings + 5 tactical spots
(agreement; oracle adjudication if diverged); 60 low-clock calls.

## Gate

50-game development screen vs frozen combined, same protocol as the
r94 head-to-head (60% + zero failures). Package only on pass.
