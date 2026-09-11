# Delta-01 candidate — 2026-09-10

New isolated candidate based on the frozen NMP champion. Only combined_search.py
changes. Quiescence search prunes non-checking captures whose static evaluation
plus generous captured-piece value plus 250cp remains below alpha. Check evasions,
promotions, checking captures, mate windows, positions of ten pieces or fewer,
and positions with a pawn within two ranks of promotion are exempt. Every skipped
capture is unmade before continuing. This is heuristic pruning, not a proof that
the skipped line is bad. No evaluation, weights, time allocation, or NMP change.

Functional verification passed: 60 legal-move/board-restoration probes, 30 actual
get_move calls with 50/250/1000ms clocks, and measurable pruning engagement.
Ten fixed-depth comparisons used 73,906 nodes versus NMP's 80,856 (8.6% fewer
in aggregate). These probes establish functionality and search-work savings only.

agent.zip in this directory is an experimental candidate, not a promoted champion.
package_verification.json records exact extraction hashes and two-colour smoke
results once packaging finishes. The repository-root NMP archive is preserved.

Development match: 50 games / 25 paired positions, seed 20260906, screen bank,
12s+0.1s per side, workers=3, against frozen search_v2_nmp_01. No early stopping.
Require at least 30 points and zero reliability failures before treating this
variant as a development improvement. Results go to vs_nmp_50g. Audit every game
and frozen manifest with tools/audit_recorded_screen.py after completion.
Final confirmation remains a separate task; this screen cannot establish it.

Reproduction: run build_candidate.py only when the variant directory does not
exist, then verify_candidate.py, then package_candidate.py. Do not mutate the
frozen variant after a match starts. Preserve interrupted evidence rather than
pooling it with a fresh run. Host sleep remains an external interruption risk.
