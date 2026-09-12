# Silky-Snow: experiment closeout

The September 7 work tested neural value integration and search overhead.
The attempted value-to-aspiration bootstrap was overwritten before use. The
candidate removed that integration and measured four search-only optimizations:
inline ordering, cheap-first futility checks, avoiding unnecessary quiescence keys,
and hoisting capture-value constants.

A ten-position depth-six comparison recorded 1.097x speed with identical moves,
scores and node counts. Late-move pruning reduced nodes more aggressively but
scored 47.0% over 100 games and was reverted. The speed-only confirmation finished
at 48.5% (+41 =15 -44); it did not establish a playing-strength gain.

The original report contains superseded running-task language and an unsupported
general claim that faster search cannot buy depth at fixed time. The neutral match
result does not establish that causal claim; time budgeting and iteration behavior
must be measured. Its original text is preserved as
[historical evidence](https://github.com/AnasBabari/MilkyWay/blob/aichessathon-2026-final-workspace/PROMOTION_REPORT_silky_snow.md).

The later `confirm_validate` report describes another speed-build comparison and
must not be substituted for this specific confirmation. See
[curated benchmarks](../BENCHMARKS.md) for the separate runs.
