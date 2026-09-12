# Build provenance

The full pre-cleanup workspace is preserved at annotated tag
[`aichessathon-2026-final-workspace`](https://github.com/AnasBabari/MilkyWay/tree/aichessathon-2026-final-workspace)
and branch `archive/aichessathon-2026-full`, both pointing to commit
`114cfa7174f2bdb876de81731abe5185dc2ce15c`.

## Three distinct facts

1. The root source calls `agent.py -> engine.py -> root_policy.py`. It defaults to
   `weights/milkyway_policy.onnx` when loading succeeds. This is the portfolio's
   preserved Python implementation.
2. The last build identified by the pre-cleanup README is
   `agent_tm_20260911.zip` (`search_v2_tm_01`). Its 12 members use original compiled
   search and `weights/compact_value.npz`, with no ONNX file. The archive is 79,562
   bytes compressed and 180,484 bytes uncompressed.
3. Neither the repository nor the owner-supplied final dashboard totals establish
   the exact last successfully uploaded archive. The event record must not be
   attributed to this ZIP alone. No final upload identity is asserted here.

The TM archive SHA-256 is
`3a829e4ea66fd897a54216fb9cf992460b3996674de408507c24c6ab7f839f2d`.
Its compact model SHA-256 is
`465ef2c4da390a359ec6e4741709093159700160a5c785b0e4b4adc53e453eca`.
The retained root ONNX model SHA-256 is
`4d93818689914495e41c1241adab1529509beacabfc2e653ff629a9a2f41e9aa`.

Download the exact ZIP and checksum from
[AI Chessathon 2026 Final Build](https://github.com/AnasBabari/MilkyWay/releases/tag/aichessathon-2026-final-build).
The source in `versions/final_packaged/` was extracted from that archive, and its
manifest covers the original twelve members. Git attributes disable line-ending
conversion for that snapshot so its hashes survive cross-platform checkout.

The loose `experiments/search_v2_tm_01` directory is not an exact substitute:
`compiled_eval.py` and `compiled_search.py` differ from the archive and its compact
model was not tracked there. Reproduction of the packaged build must start with
the ZIP, not that directory or the root source.

The old root `agent_manifest.json` describes an earlier speed build and includes
an unused flagship model. It is historical evidence, not a current build manifest.
The larger flagship ONNX variants and external `.onnx.data` companion are not
loaded by the root's default policy path. `neural_value.py` was an unused root
experiment wrapper for a different model, not part of the default call chain.

## Recovery

```bash
git fetch origin --tags
git worktree add ../MilkyWay-history aichessathon-2026-final-workspace
```

This restores the original paths, raw reports, models, campaign launchers and
intermediate archives without rewriting history or mixing them into the maintained
checkout. Historical manifests may contain machine-specific absolute paths.
