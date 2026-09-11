# Astralix v2 — LMR check exclusion (guarded)

Base: v1-trimmed (policy ordering + depth-limit removal, no value scaling),
plus exactly one mechanism: **late quiet checking moves are excluded from
LMR** and searched at full depth. Rationale: a quiet check is the most
forcing quiet move; reducing it blinds tactics (R34 §4 hypothesis; cf.
41.Rf3??-class misses). Consistent with the existing futility exemption
for checking moves.

## Safety history (read before touching gives_check)

2026-09-07: the unguarded form (`and not board.gives_check(move)`)
crashed 12/12 tournament games. Forensics: `gives_check()` pushes
internally and asserts pseudo-legality; on an illegal input the push
raises *before* saving state while `finally: pop()` still runs, stealing
the caller's pushed move. Each theft permanently desyncs board/stack
(silent shuffling, then illegal-move crash). The `is_pseudo_legal` guard
is pure bit operations with no push/pop, so the theft is unreachable by
construction. `order_root_moves` carries the same guard.

## Status

Experimental. Gates before any claim: crash-FEN repro, mate/tactics
suite, ruff clean, then SF6 screen on the standard 6 pairs vs the 41.7%
policy-only reference.
