# Search V2 architecture audit — 2026-09-08

Status: source inspection complete for the compiled search path; baseline selection and instrumented experiments pending the two parent comparisons. This is an engineering audit, not evidence that Search V2 is stronger. No playing runtime was modified.

Inspected: compiled_pvs_01/{agent.py,core.py,compiled_search.py,pvs_search.py,time_manager.py}, compiled_ordered_01/ordered_search.py, compiled_sf7_rl_01/manifest.json, and the relevant silky_snow/search.py sections. Per-file identities are captured in BASELINE_MANIFEST.json. The RL variant has the PVS search with different weights; it does not include the ordered variant's change.

The reference engine is deliberately conservative. Speeding up its board operations did not recreate the selective search present in silky_snow. That makes search a plausible bottleneck, but the relative contributions of evaluation, ordering, quiescence and pruning have not been measured sufficiently to assert causation.

| Component | Compiled state | Evidence / concern | Next check and priority |
|---|---|---|---|
| Board / make-unmake | Present; tested, not exhaustively proven | Signed 64-square array, explicit castling/EP/promotion. Existing five perfts, 1,000 positions and 30,790 transitions passed. | Preserve independent python-chess parity; add pinned EP and promotion exchange cases. P0 |
| Legal generation | Present-weak for speed | generate supports captures_only; legal_moves always requests full generation and filters by make/unmake. Allocates up to 512 moves per node. | Count generated vs searched moves and generation time; staged legal capture generation is a separate mechanism. P1 |
| Iterative deepening | Present-correct within existing tests | Full depths retained only when complete; last legal move is fallback. | Aborted iteration must not leak score/move or board/history. P0 |
| PVS | Present; tested | First move full window, later moves scout, full re-search inside window. Qsearch uses full windows. | Count scouts/re-searches, compare unselective reference at fixed depth. P0 |
| Aspiration | Absent | Every root iteration uses the full mate window. | Independent later variant with widening, mate guards and deadline tests. P2 |
| TT key | Present-weak for cost | Full 64-square FNV recomputation; legal EP identity. | Measure key cost before proposing incremental hashing; test all special moves if changed. P1 |
| TT bound context | Present-conservative | Halfmove, root ply and reversible-history multiset guard bounds. Exact depth equality. | Existing poisoned-context tests retained. Measure rejected hits; never remove history safeguards solely for speed. P0 |
| TT depth/replacement | Present-weak | Single slot always replaced; depth equality restricts reuse; tables allocated anew each move. | Separate replacement/retention/depth experiments. Deeper-entry reuse changes fixed-depth semantics and needs its own oracle. P2 |
| TT exact/lower/upper | Present; tested | Original alpha classifies stores; bound and mate conversions exist. No Q TT. | Window-edge, collisions, mate-distance and aborted-store tests. P0 |
| Hash move legality | Present-suspicious | Ordering operates on a legal list, but a bound hit directly returns stored move without explicit membership check. Normal same-key entries are legal; collision/poison resilience untested. | Inject an invalid stored move; require legal root fallback and no invalid move execution. P0 |
| Game isolation | Present by allocation/protocol | TT rebuilt per call; module history maintained by identifying a legal opponent move, reset on mismatch; platform new process per game. | History reset and consecutive-game tests retained. P0 |
| Quiescence | Present-weak for work | Full legal generation before stand-pat; captures and all promotions searched; all check evasions. No SEE or delta pruning. | Q-node share, max q-depth, generated/searched counts, checked leaf tests. P1 |
| Terminal / draw ordering | Present-correct within tests | Mate/stalemate checked before 50-move/repetition/insufficient draw. | Boundary mating move, 99/100 halfmoves and legal-EP repetition probes. P0 |
| Q/search depth cap | Present-suspicious | Global ply 96 stops with static eval, including checked positions with legal evasions. Protects stack but may distort forced checks. | Construct long checking lines and report cap hits; no assertion that checked static leaves are safe. P0 |
| SEE / QSEE / delta | Absent | Capture ordering is MVV-LVA, not exchange evaluation. | First implement own legal exchange oracle/tests; initially use SEE for ordering only. Pruning later separately. P1 |
| Killer / quiet history | Absent in PVS/RL; present in ordered | Two killers per ply, bounded gravity bonuses/maluses; reset each search. Earlier 16-position test saved nodes, tournament pending. | Wait for full parent result; telemetry first-move cutoff and history effectiveness. P1 |
| Capture / counter / continuation history | Absent | No such tables or update paths in inspected compiled search. | Distinct later mechanisms; never bundle with quiet-history changes. P2 |
| LMR | Absent from all three frozen candidates | Isolated reduced_search prototype exists outside playing lineage. Depth-four work slightly increased; four depth-six cases improved work. | Broader tactical/zugzwang/checking probes and re-search counters before freezing. P1 |
| Null move | Absent | No synthetic pass or verification path. | Add only after baseline/ordering, with non-pawn-material, check, mate and zugzwang safeguards; isolate synthetic history. P1 |
| Reverse / shallow futility | Absent | No static forward-pruning tests in compiled path. | Separate low-depth variants; retain at least one legal searched move, check/promotion/mate protections. P2 |
| LMP / history pruning / SEE pruning | Absent | No late-move skip or exchange threshold. | Separate mechanisms after ordering and tactical coverage. P2 |
| IIR / ProbCut / singular extension | Absent | No supporting paths. | Defer until ordinary selective search demonstrates value. P3 |
| Check extension | Absent | Qsearch handles checks, but main depth is not extended. | Test bounded extension separately; never allow checking cycles to defeat time/ply limits. P2 |
| Mate-distance window pruning | Absent | Mate scoring/normalization is present, window tightening is not. | Independent exact-search optimization with mate tests. P2 |
| Time / telemetry | Present-weak for diagnosis | Poll every 128 nodes; soft/hard limits plus IPC reserve. Returned elapsed time omits allocation before local timer, while outer agent clock includes call time. tt_hits actually counts cutoffs only. | End-to-end vs kernel timings, clock overshoot, honest named counters. No tuning time allocation during search ablations. P0 |

Silky comparison: its own Python search already has aspiration, null move, LMR, reverse/shallow futility, quiet history/killers, check extension and qsearch delta pruning. These are not automatically safe templates: inspected code applies some pruning before legal terminal detection, TT bounds lack the compiled history-context guard, and checked qsearch has a static cap. Study our historical behavior, but independently test any new compiled implementation.

Priority decision: establish telemetry and correctness coverage first. Then ordering/SEE, LMR and verified null move are plausible first candidates. Full legal-generation cost and conservative TT reuse deserve measured follow-up. Do not change evaluation or train new weights at the same time. Do not treat this feature inventory as proof every listed technique helps this engine.
