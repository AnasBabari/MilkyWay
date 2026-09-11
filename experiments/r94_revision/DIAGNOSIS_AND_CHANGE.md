# Round 94: actual engine revision

User correction: improve the engine that lost, not merely rebuild its ZIP. User supplied the PGN and prohibited computer-skill use; all further work uses local files and tools only.

## Evidence

The supplied PGN is legal and ends in checkmate against The Veritys. White had 21.265 seconds left after its last move; this loss was not a flag. The game contains 41 white moves from a London System starting position.

Offline Stockfish at 100,000 nodes per unrestricted/forced move identifies 14.Qc2, 21.Nc5, and especially 26.Qd2 as important mistakes before the decisive attack. At move 26, queenside castling remains legal. A separate 200,000-node forced comparison estimates Qd2 at -374cp and O-O-O at +36cp. These are bounded diagnostics, not perfect ground truth or ratings.

The frozen combined engine repeats Qd2 in a matched 4-second hard / 2-second soft probe. It treats its exposed king too optimistically. Later queen/rook attacks enter while its king stays in the centre. Search quality and evaluation both matter; this test isolates an evaluation change first.

## Actual change

New isolated runtime: experiments/r94_king_safety_01. Exactly one runtime file differs from experiments/search_v2_combined_01: compiled_eval.py. The added feature penalizes a king on a central file with missing pawn cover when the enemy has a queen, with pressure scaled by remaining enemy rooks and the king's rank. It is symmetric between colours and disabled when the enemy queen is absent. This is a general formula, with no game-specific positions or move lookup table.

Search, move generation, neural weights, and clock settings are unchanged. All old runtimes and the existing ZIP remain preserved until the new candidate passes its test and smoke gates.

## Verification completed

- The old engine chooses 26.Qd2; the new candidate chooses 26.O-O-O at identical fixed probe budgets.
- At the actual recorded 51,114ms remaining, the new candidate returns O-O-O in 1.806s through get_move.
- It develops Be2 instead of 10.g4; offline forced analysis estimates a 70cp improvement there.
- All 60 pre-existing suite positions return legal moves and restore their boards; all 60 short-clock calls pass.
- The new feature is exactly colour symmetric on the suite. The baseline evaluator has existing small mirror differences; the candidate adds zero difference to those observed deltas. No claim that the entire baseline is symmetric.
- Eight short-budget suite decisions changed. Offline review includes one -241cp difference in an already losing position. This downside is preserved; the candidate must prove itself in direct games.
- Static package preflight matches the frozen manifest; 180,010 bytes unzipped. Lint passes for the new helper/scripts. Existing untyped engine functions are not claimed strict-mypy clean.

## Active test and remaining work

Direct 50-game screen against the actual losing combined runtime: 25 reversed-colour pairs, 12s+0.1s, 3 workers, seed 20260906, existing screen bank. Protocol in head_to_head_protocol.json requires >=60% score, zero reliability failures, full completion and audit; no early positive stop. Raw records: king_safety_vs_combined_50g. Writer session15536 at launch; revalidate before relying on it.

finish_candidate.py can wait for this exact run, audit it, and package only if the gate passes. It then verifies deterministic archive construction, clean extraction hashes, and both unchanged-harness smoke games. It backs up the old root ZIP before delivery. A failure preserves the old ZIP and leaves the task requiring further engine work.

This is a development comparison. It does not establish independent full-clock superiority against all previous candidates. Do not mark the overarching campaign goal complete based on it alone.
