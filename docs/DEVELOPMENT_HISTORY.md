# Development history

The competition is complete. This is a retrospective, not an active milestone queue.

1. **Starter and MW-0.1:** established the protocol, then implemented the complete
   classical engine: evaluation, iterative deepening, PVS, quiescence, TT, pruning,
   ordering and time management.
2. **MW-0.2:** profiled object overhead, introduced bitboard evaluation and bounded
   cache eviction, and repaired low-clock deadline behavior. Frozen MW-0.1 and
   MW-0.2 source remains in `versions/` for comparisons.
3. **M16:** parameterized the evaluator, extracted interpretable features and fitted
   coefficients. The candidate missed the precommitted promotion threshold.
4. **M17–M19:** developed offline policy training, root ONNX integration, rated-game
   forensics and paired qualification tools. RC1 failed the combined strength and
   full-clock gates despite clean execution in its recorded campaign.
5. **Silky-Snow:** investigated a value head and search overhead. Late-move pruning
   was reverted; speed-only measurements were separated from uncertain game gains.
6. **Compiled Search V2:** explored original Numba search, staged generation and LMR,
   then null-move and middlegame revisions. Host sleep invalidated an independent
   confirmation; existing evidence informed an owner-directed packaging decision.
7. **TM revision:** increased healthy-clock move ceilings. The completed 20-game
   diagnostic scored 16/20; no completed independent 100-game confirmation is
   established. This was the last documented package, not a verified final upload.
8. **Event close:** owner-provided record +47 =12 -43 over 102 rated games, peak
   event Elo 1556. Cleanup preserved history and made no strength changes.

See [experiments](EXPERIMENTS.md), [benchmarks](BENCHMARKS.md) and the
[postmortem](POSTMORTEM.md). The original milestone checklist and all raw campaign
notes remain in the [historical workspace](https://github.com/AnasBabari/MilkyWay/tree/aichessathon-2026-final-workspace).
