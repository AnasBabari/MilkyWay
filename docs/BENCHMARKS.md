# Curated benchmarks

The final owner-supplied dashboard result is **102 rated games: +47 =12 -43**,
with **peak event Elo 1556**. These event figures are separate from local arenas.
No local run below establishes the identity of the final platform upload.

## Historical measurements: legacy harness

MW-0.1, MW-0.2 and M16 records used the earlier harness with a 300-ply cap and
material adjudication. They are historical engineering evidence, not results
generated under the final 600-ply draw rule. The original benchmark log records
a local Windows host and Python 3.14.5 for early work, not competition hardware
or the final Python 3.12 environment.

| Stage | Method | Recorded result |
| --- | --- | --- |
| Starter | 20 games vs greedy, 10s+0.1s | 10.0%, +0 =4 -16 |
| MW-0.1 | 20 games vs greedy, 10s+0.1s | 100%, +20 =0 -0 |
| MW-0.1 | 20 games vs numba baseline, 10s+0.1s | 97.5%, +19 =1 -0 |
| MW-0.2 | 100 games vs MW-0.1, 10s+0.1s | 96.0%, +93 =6 -1; one flag prompted a clock fix |
| M16 Huber fit | 100 games vs MW-0.2, 0.5s+0.05s | 53.0%, +48 =10 -42; rejected below 55% gate |

### Optimization evidence

- Evaluation: 5,225 -> 14,774 calls/s (2.83x). The bitboard rewrite was checked
  against MW-0.1 on two 2,000-position batches, with zero score mismatches.
- Search: depth four on 20 positions, 170,911 nodes / 33.95s (5,034 NPS) before;
  174,995 nodes / 16.64s (10,519 NPS) after. Throughput rose 2.09x; node counts
  were close but not identical, so this is not strict search parity.
- Low-clock probe: 67/320 overruns before the deadline-floor/polling fix, 0/320
  afterward. This is a historical host probe, not a guarantee at every clock.

## Historical measurements: later harness

These records followed the 600-ply draw-cap synchronization. Time controls and
sample sizes still differ; do not merge them into one strength estimate.

| Experiment | Games / clock | Score and evidence | Interpretation |
| --- | --- | --- | --- |
| M18 RC1 pooled screen + holdout | 400, 10s+0.1s | 52.125%, +176 =65 -159; paired CI 48.75–55.5% | Exploratory pool; below target, interval spans neutral |
| M18 policy ON/OFF | 40, 10s+0.1s | 50.0%, +18 =4 -18; CI 35–65% | No established policy gain |
| M18 full-clock bridge | 20, 120s+0.5s | 45.0%, +7 =4 -9; CI 30–57.5% | Direction reversed; promotion rejected |
| Silky-Snow late-move pruning | 100, 10s+0.1s | 47.0%, +37 =20 -43; CI 38–56% | Reverted despite lower node count |
| Silky-Snow speed-only confirmation | 100, 10s+0.1s | 48.5%, +41 =15 -44; CI 40–58% | No demonstrated match gain in this test |
| Search V2 combined vs Silky-Snow | 50, 12s+0.1s | 88.0%, +43 =2 -5 | Strong short-clock screen; not full-clock confirmation |
| Search V2 pooled full-clock | 48 scored, 120s+0.5s | Historical promotion report: 59.4%, +25 =7 -16 | 20 predeclared + 30 extension; one void and one sleep-flag excluded |
| TM diagnostic vs Silky-Snow | 20, 120s+0.5s | 80.0%, +15 =2 -3; paired CI 65–92.5% | Ten opening pairs; no failed terminations; not independent confirmation |

The separate 100-game combined confirmation was disqualified by a host sleep/wake
artifact. Its partial result is not a completed gate. The earlier M18 record
reported zero crashes, flags or illegals across 540 games; this is scoped historical
reliability evidence, not a claim that the project never experienced a failure.

### Evidence locations

- [M18 final report](../experiments/m18/final_report.json)
- [Silky-Snow pruning confirmation](../experiments/silky_snow_promo/report_100.json)
- [Silky-Snow speed confirmation](../experiments/silky_snow_confirm/report_100.json)
- [Combined short-clock report](../experiments/search_v2/combined_live_12s_50g/report_50.json)
- [Invalidated confirmation](../experiments/search_v2/confirm_combined_live_120s_100g/reliability_disqualification.json)
- [TM trial](../experiments/tm_revision/tm_fullclock_20g/report_20.json)
- [Original full benchmark log](https://github.com/AnasBabari/MilkyWay/blob/aichessathon-2026-final-workspace/BENCHMARKS.md)
- [Historical combined promotion report](https://github.com/AnasBabari/MilkyWay/blob/aichessathon-2026-final-workspace/experiments/search_v2/PROMOTION_REPORT_COMBINED.md)

## Current cleanup verification

No new strength campaign was run during portfolio cleanup. Current lint, type,
unit, gate and package-smoke outcomes are recorded in the
[cleanup report](cleanup/REPORT.md). Historical timings above were not remeasured.
