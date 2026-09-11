# SEE-01 — capture ordering candidate, 2026-09-10

Base: frozen search_v2_nmp_01. Delta-01 finished +22 =14 -14 (58%, 29/50),
one point below the predeclared development gate. It remains unqualified.
SEE-01 is a distinct mechanism on NMP; no Delta pruning is inherited.

NMP prioritizes captures by captured-piece value and attacker value. SEE-01
additionally follows the least valuable legal recapturer on the destination
square, updating occupancy so revealed sliding attacks and pins are respected.
Each side may stop the exchange. Losing captures are ordered behind quiet moves;
the TT move and promotions retain their existing priority. No move is removed.

This estimate is deliberately limited to a material exchange on one square.
It does not solve tactics, intermediate moves, alternative attacker choices, or
underpromotions. It is used only for ordering. Ordering also changes which quiet
moves receive NMP's existing late-move reductions, so playing strength still
requires a match rather than being inferred from node counts.

Changes: new capture_order.py, plus combined_search.py integration and counters.
All other runtime files, weights, evaluation and clock allocation match NMP.
The implementation was written for this project; no external engine is included.

Verification: verify_candidate.py independently checks the estimates against
python-chess legal captures on curated and random positions, then runs legality,
board-restoration, fixed-depth-work and actual low-clock get_move probes.
verification.json is written only when every assertion passes.

Completed preflight: 306 exchange-reference comparisons, 60 legal/restored search
probes and 30 low-clock calls passed. Ten depth-4 comparisons searched 66,674
nodes versus NMP's 80,856 (17.5% fewer), choosing the same root move in all ten.
Measured search time was 0.193s versus 0.204s in total; this short timing sample
is too noisy for a general speed claim. Neither result establishes strength.

package_candidate.py audits and deterministically builds this directory's
agent.zip, verifies extracted hashes, and runs the unchanged two-colour harness
smoke. package_verification.json records completion. This is an experimental
archive; the repository-root NMP champion archive is preserved.

run_screen.py starts one 50-game NMP comparison: 25 paired openings, screen bank,
seed 20260906, 12s+0.1s, workers=3, recorded games and frozen manifests.
It requires completed package verification, refuses existing output directories,
finishes all games, audits them, and records the 30/50-point development gate.
It never promotes automatically. Strength remains unproven until results arrive.

Watch screen.log or inspect screen_status.json. Output is vs_nmp_50g.
Do not mutate the candidate after the match starts. Final independent full-clock
qualification remains separate. Interrupted evidence must not be pooled into a
fresh run, and host sleep must be resolved before an overnight confirmation.
