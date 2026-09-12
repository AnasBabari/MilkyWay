# AI Chessathon 2026: engineering postmortem

MilkyWay finished with **102 rated games: 47 wins, 12 draws and 43 losses**, and a
**peak event Elo of 1556**. These are the project owner's final dashboard figures.
The score was 53/102 points (52.0%). No placement, award or percentile is claimed.

## Challenge and constraints

The task was to turn a FEN and a remaining wall-clock budget into one legal UCI
move. The historical competition contract specified Python 3.12, one CPU core,
2 GB RAM, no network or GPU, 120 seconds plus 0.5 seconds per move, a separate
90-second qualifier import budget (30 seconds at the final) and a 50 MB
uncompressed submission. These constraints
made search efficiency, predictable latency and packaging correctness central.

The official [rules](https://aichessathon.com/docs/rules.md) and
[agent contract](https://aichessathon.com/docs/agent-contract.md) were retrieved
directly during cleanup on September 13, 2026, after browser retrieval failed.
These numbers describe that event contract, not a future event configuration.

## From starter to engine

The official starter supplied a legal random mover, baselines, a process protocol,
referee and local arena. The first MilkyWay engine added iterative deepening,
PVS/alpha-beta, a bounded transposition table, tactical quiescence, move ordering,
pruning and a tapered handcrafted evaluation. The goal was a complete decision
pipeline whose performance could be measured against frozen previous versions.

MW-0.2 concentrated on overhead. Profiling identified evaluation, attack queries,
move generation and ordering costs. Bitboard evaluation removed temporary objects;
leaner ordering removed repeated work; constant-time table eviction bounded a
potential long-game latency spike. Historical measurements showed evaluation
throughput rising from 5,225 to 14,774 calls/s and depth-four search from 5,034 to
10,519 nodes/s. Differential testing checked exact evaluation parity before games
tested the whole change. These are local historical measurements, not current
platform benchmarks.

## Reliability was part of strength

A flag in the 100-game MW-0.2 comparison exposed clock floors and coarse deadline
polling that failed with little time remaining. Timing probes found 67 overruns
in 320 calls before the fix and none in the repeated probe after it. This was more
informative than a small collection of clean games. Legal-position fuzzing,
regression FENs, package extraction and clock probes became complementary checks.

## Evaluation and neural experiments

M16 fitted interpretable evaluation coefficients with game-separated data splits.
The Huber candidate improved held-out error but scored 53.0% over 100 fast games,
below its precommitted 55% promotion threshold. Better fitting loss was insufficient
evidence of better decisions under search.

Offline GPU work trained team-owned models and exported ONNX for CPU inference.
The Python root policy scored legal moves once at the root to avoid per-leaf
inference cost. In M18, policy ON versus OFF scored 50.0% over 40 games, with a
wide interval. RC1 scored 52.125% in the exploratory 400-game pool but only 45.0%
in the 20-game full-clock bridge. It failed the promotion protocol. These results
do not support attributing engine strength to the policy network.

The Silky-Snow value experiment improved validation loss, but its attempted
aspiration bootstrap was overwritten before use. Leaf inference was too expensive
for that integration. Late-move pruning saved nodes but scored 47.0% in its
100-game confirmation and was reverted. The lesson was to test that an idea
actually influences decisions, then test whether those decisions improve games.

## Later search work and final package

Later work explored original Numba search, staged quiescence generation and LMR,
then null-move, middlegame and time-management revisions. The combined candidate
scored 88.0% against Silky-Snow in a 50-game short-clock screen. The historical
full-clock pooled report recorded 59.4% over 48 scored games after exclusions.
An independent confirmation was disqualified by a host sleep/wake artifact. It
did not become a completed confirmation merely because the event ended.

The final documented TM trial completed at 15 wins, 2 draws and 3 losses in 20
games at 120s+0.5s. This was a diagnostic on ten opening pairs, not the missing
independent 100-game test. The packaging decision and evidence limitations are
part of the engineering record.

The repository's root Python engine and last documented compiled TM package are
different implementations. The latter uses a compact learned residual rather than
the root ONNX policy. The exact last successful platform upload is not established
by the surviving repository. [Build provenance](BUILD_PROVENANCE.md) records this
distinction and the archive checksum.

## Live observations

Rated-game analysis turned concrete losses against LarpMaxx and Neomatica into
mate-delay and tactical regression positions. Later clock logs motivated studying
whether healthy-clock move ceilings starved critical decisions. These observations
generated hypotheses; replay outcomes and small match samples could not by
themselves establish tournament-wide effects.

The final event record was positive by four wins. Peak event Elo is an event-local
dashboard statistic, not a calibrated human rating or a measure against unrelated
engine leaderboards.

## Lessons and next work

- Measure the expensive path before changing it; lower allocation overhead can
  matter as much as an additional search heuristic.
- Keep game/opening pairs together in uncertainty estimates and preserve an
  untouched confirmation bank. Repeated screening consumes its independence.
- Test at the clock where the changed branch executes. Short-clock matches could
  not evaluate a time-manager change restricted to healthy clocks.
- Separate held-out prediction error, fixed-depth speed, match score and live
  results. None is an interchangeable proxy for the others.
- Freeze packages as well as source. Loose candidate directories and stale
  manifests can diverge from an archive that actually ran.
- Control host load and sleep during wall-clock experiments. Infrastructure can
  invalidate a match without a chess-engine defect.

With more time, the next steps would be an independently frozen full-clock
comparison, systematic move-generation profiling, more sparse-endgame and
zugzwang regressions, and separate ablations of the compact residual. These are
research directions, not changes made in this cleanup.
