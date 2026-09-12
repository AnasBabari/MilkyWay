# AI Chessathon 2026 Final Build

The exact **last documented packaged build** from the MilkyWay research workspace:
`search_v2_tm_01`, packaged September 11, 2026. This is not independently verified
as the final successful platform upload.

- Archive: `agent_tm_20260911.zip`, 79,562 bytes compressed / 180,484 uncompressed.
- SHA-256: `3a829e4ea66fd897a54216fb9cf992460b3996674de408507c24c6ab7f839f2d`.
- Original compiled search with a team-trained compact value residual; no ONNX
  root policy is included in this archive.
- Completed TM diagnostic: 15 wins, 2 draws, 3 losses at 120s+0.5s. The missing
  independent 100-game confirmation is not represented as complete.
- Final owner-provided event totals: 102 rated games, 47 wins, 12 draws, 43 losses,
  peak event Elo 1556. These totals are not attributed exclusively to this package.

The full pre-cleanup workspace is preserved by annotated tag
`aichessathon-2026-final-workspace` and branch `archive/aichessathon-2026-full`.
The portfolio root is a separate Python implementation with optional ONNX root
ordering. See the repository's build-provenance document before reproducing a run.
