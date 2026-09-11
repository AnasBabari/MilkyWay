# TM-ceiling candidate: design note

Isolated variant `experiments/search_v2_tm_01`: byte-copy of frozen NMP plus
ONLY raised healthy-clock single-move caps (`time_manager.py`):
soft 3.5s -> 6s, hard 6.5s -> 12s, applied exclusively in the
`time_left > 90000` branch. Emergency / low-clock / margin / single-move
paths are byte-identical.

## Evidence

- Every rated game log pegs slowest-move at the 6.5s hard cap with 20-100s
  remaining: the cap binds on at least one (usually the most critical) move
  per game.
- Habitual spending (~3s = usable/40 + 0.7*inc) sits BELOW the old soft cap,
  so only starved critical moves change behavior; baseline spending is kept.
- Middlegame time probe: extra time converted >=1 corpus blunder outright;
  remainder need depth-per-node work (separate track).

## Why not a 12s screen

At 12s+0.1s, `time_left > 90000` never holds, so the patched branch cannot
execute: any 12s result would be noise by construction. Efficacy is measured
by a pooled full-clock trial on the identical 10 pairs combined scored 10/20
on (bands: >=12.5 suggests gain; <=8.5 suggests harm). A 12s legality +
12s-identical-moves check guards the patch instead.
