# Check-extension candidate: design and verification plan

Isolated variant `experiments/search_v2_checkext_01`: byte-copy of frozen
NMP (`search_v2_nmp_01`) plus ONLY one-ply extensions for checking moves at
depth>=1 nodes (builder: `experiments/checkext_revision/build_checkext_candidate.py`).

## Design

- After make_move, `gives_check = attacked(enemy king, us)` on the legal
  post-push board (same proven-safe pattern as the LMR exclusion test).
- All child searches of that move use `child_base = depth - 1 + 1`.
  LMR never applied to checks anyway; extension composes with it.
- Quiescence untouched (depth<=0 paths keep depth-1).
- Ply LIMIT=96 caps runaway checking lines; TT/deadline behavior unchanged.
- Rationale: both rated mates (R94 infiltration, R97 ...Rg2+/Qf2#) came via
  forcing sequences. Finding forced mates one ply deeper is the cheapest
  classical tactic lever left (aspiration was rejected; NMP already taken).

## Verification

Same bar as NMP: 240-suite legality, fixed-depth node behavior (extension
costs nodes by design — measure, don't gate), mates/tactics agreement,
pawn endings, 60 low-clock calls. Then 50-game screen vs NMP (60% + zero
failures). Package only on pass.
