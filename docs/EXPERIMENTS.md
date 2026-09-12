# Selected experiments

The working method was **PROFILE -> HYPOTHESIS -> CHANGE -> MEASURE -> ARENA ->
KEEP / REVERT**. Paired openings, held-out banks, uncertainty intervals and frozen
opponents mattered more than an isolated favorable score.

| Experiment / hypothesis | Change | Evaluation method | Result | Decision |
| --- | --- | --- | --- | --- |
| MW-0.2: Python overhead limited depth | Bitboard evaluation, lean ordering, FIFO TT | Differential positions, depth-four suite, 100 games vs MW-0.1 | 2.83x eval/s; 2.09x NPS; 96.0% historical match score | Kept; legacy harness caveat applies |
| M16: fitted coefficients improve play | Huber fit with sound mobility bounds | Held-out prediction error; 100 games vs MW-0.2 at 0.5s+0.05s | 53.0%, below 55% threshold | Rejected for promotion |
| M18: policy-assisted RC1 improves the engine | Root ONNX ordering and candidate bundle | 400-game pool; policy ablation; full-clock bridge | Pool 52.125%; policy ablation 50.0%; full-clock bridge 45.0% | RC1 rejected under the precommitted protocol |
| Silky-Snow: deeper pruning buys strength | Late-move pruning | 50 paired openings, 10s+0.1s | 47.0% (+37 =20 -43), CI 38–56% | Reverted |
| Silky-Snow: less overhead preserves decisions | Ordering and quiescence micro-optimizations | Depth-six parity; 100-game confirmation | 1.097x fixed-depth speed; 48.5% game score | Speed evidence retained; no proven playing gain from that test |
| Search V2: staged generation and LMR improve compiled search | Combined original search changes | 50-game short-clock screen vs Silky-Snow; pooled full-clock games | 88.0% short-clock; historical pooled full-clock report 59.4% over 48 scored | Packaged by owner decision; independent confirmation invalidated by host sleep |
| TM revision: raised healthy-clock ceilings help critical moves | Larger caps only above 90 seconds remaining | Ten paired openings at 120s+0.5s | 80.0% (+15 =2 -3), paired CI 65–92.5%; no failed terminations | Last documented package; diagnostic evidence, not independent confirmation |

The ONNX policy remains enabled by default in the preserved root implementation.
That does not reverse the historical RC1 promotion decision or establish that the
network improved playing strength. The later packaged engine used a different
compact learned residual; see [provenance](BUILD_PROVENANCE.md).

## Reading the evidence

The [benchmark summary](BENCHMARKS.md) separates old 300-ply material-adjudication
measurements from later 600-ply draw-cap measurements and the final dashboard.
Raw reports retain their historical candidate names, paths and partial-run fields;
they must not be treated as current instructions to launch a campaign.

The complete experiment tree, including rejected candidates and raw game outputs,
is available in the
[pre-cleanup snapshot](https://github.com/AnasBabari/MilkyWay/tree/aichessathon-2026-final-workspace/experiments).
Restore that snapshot in a separate worktree to run historical scripts with their
original inputs. Dataset downloads and ignored local training intermediates were
not part of the tracked workspace and are not promised by that snapshot.
