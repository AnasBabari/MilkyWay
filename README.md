# AI Chessathon starter

Fork this to build an agent for [AI Chessathon](https://aichessathon.com). It gives you a working
submission, baselines to beat, and a local harness that speaks the same protocol and enforces the
same clock as the platform, so you can see whether a change actually helped before you upload it.

```
git clone https://github.com/advitrocks9/aichessathon-starter
cd aichessathon-starter
make setup
make play
```

That plays your agent against a baseline over a full 120 s + 0.5 s game and prints the result.
When you like it, `make zip` and drop `submission.zip` on your dashboard.

## Writing an agent

`agent.py` is the whole submission. One function:

```python
def get_move(fen: str, time_left_ms: int) -> str:
    return "e2e4"
```

The fork ships a legal random-mover, so the loop works before you write anything. Replace the body.

```
make play                                          # one game, real time control
make arena                                         # 20 fast games, prints a score
make play FEN="<fen>"                              # start from a given position
uv run python -m harness.play --black baselines/minimax --pgn game.pgn
uv run python -m harness.arena --opponent ../my-old-version --games 200
```

Anything your agent prints shows up under the result, so `print` debugging works. The platform
keeps it too. Every rated game leaves a log on your dashboard next to the PGN, holding your
output plus your init time, your time on each move, and the clock you had left. Only your team
can read it.

## The ladder

Measured with `harness/arena.py`. Beating greedy is a search. Beating minimax is a search plus an
evaluation worth searching with.

| Matchup | Games | Time control | Score |
|---|---|---|---|
| random vs greedy | 20 | 10 s + 0.1 s | 10.0% (+1 =2 -17) |
| greedy vs minimax | 6 | 120 s + 0.5 s | 0.0% (+0 =0 -6) |
| numba vs minimax | 6 | 10 s + 0.5 s | 66.7% (+2 =4 -0) |

- `baselines/random` plays a uniformly random legal move. It is what `agent.py` starts as.
- `baselines/greedy` searches one ply on material.
- `baselines/minimax` searches two plies on material and mobility, with no time management.
- `baselines/numba` is `minimax` with the evaluation jitted. It is barely stronger, which is
  the point: jitting a shallow search buys headroom, not depth. Read it for the warm-up call
  at the bottom, which is how you keep compilation off your clock.

## What's here

```
agent.py             your submission
baselines/           random, greedy, minimax, numba; each is a directory with an agent.py
harness/runner.py    the process the platform runs your agent in
harness/referee.py   the clock, legality, draw and adjudication rules
harness/rules.py     the event constants the harness enforces
harness/sandbox.py   the one process, spoken to as the platform speaks to a container
harness/play.py      one game between two agent directories
harness/arena.py     many games, with a score
harness/package.py   builds submission.zip with agent.py at the root
docs/IDEAS.md        where the strength actually comes from
```

Local games start from the normal position unless you pass `--fen`. Rated games start from
curated neutral positions.

The harness is here so your games are honest, not so you can pre-validate an upload. Acceptance
happens on the platform, and the validation log on your dashboard is the authority on it.

## The rules

[aichessathon.com/docs](https://aichessathon.com/docs) is canonical and changes. Read it before
you upload.

## MilkyWay (our agent)

Classical competition engine, no network. `agent.py` is a thin wrapper that
validates the FEN, calls the persistent `MilkyWayEngine`, and re-validates the
returned UCI so an engine bug can never surface as an illegal move.

```
agent.py            competition entrypoint (get_move)
engine.py           persistent game state, fallback move, repetition avoidance
search.py           iterative deepening + PVS alpha-beta + quiescence + pruning
evaluation.py       tapered handcrafted eval (centipawns, side-to-move relative)
move_ordering.py    TT move, promotions, MVV-LVA, killers, history, checks
transposition.py    bounded TT with generations (EXACT/LOWER/UPPER)
time_manager.py     soft/hard deadlines + emergency mode (time.monotonic)
constants.py        scores, PSTs, tunable eval coefficients
engine_types.py     TTEntry, SearchStats, SearchTimeout
tests/              32 unit tests (contract, eval, search, tactics, time, TT)
tools/              eval/search benchmarks, fuzzing, arena matrix
```

Search details: negamax with mate-distance scores (`MATE - ply`), TT cutoffs
with mate adjustment, null-move pruning (not in check, non-pawn material,
depth >= 3), LMR on late quiet moves with re-search, futility/reverse-futility
at shallow depths, limited check extensions, aspiration windows from depth 4,
delta pruning in quiescence, repetition/fifty-move/insufficient-material draws.
TT, killers, history and game history persist across moves in a game.

Time control: 120 s + 0.5 s. Soft deadline stops new iterations, hard deadline
aborts search; emergency mode (<6 s, critically <1.2 s) caps depth and
quiescence width. A mating/capturing fallback is chosen before search starts.

Local testing:

```
uv run python -m unittest discover -s tests
uv run python -m tools.fuzz_positions --positions 500 --time-ms 200
uv run python -m tools.benchmark_eval --positions 2000
uv run python -m tools.diff_eval --positions 2000       # eval parity gate
uv run python -m harness.arena --opponent baselines/numba --games 20
uv run python tools/paired_arena.py --opponent versions/mw_0_1   # 40 FENs x2
uv run python -m harness.package  # submission.zip, agent.py at root
```

Current version: **MW-0.2** (2.09x search NPS over MW-0.1, 96.0% over
100 games, low-clock flag fixed and probed). MW-0.1 snapshot in
`versions/mw_0_1/` is the standing A/B opponent; `tools/paired_arena.py`
plays the 40-position bank with colours reversed. Numba was measured and
rejected: no qualifying hotspot. Details in `BENCHMARKS.md`.

Constraints honoured: only `chess` (+ stdlib) at runtime, single thread, no
network, no native binaries, deterministic move selection, readable source.
Milestones and results live in `IMPLEMENTATION_PLAN.md` / `BENCHMARKS.md`.
