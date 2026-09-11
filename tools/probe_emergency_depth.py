"""Compare emergency depth caps at identical real budgets on recorded positions."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import chess


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.agent.resolve()))
    engine = importlib.import_module("engine")
    tm = importlib.import_module("time_manager")
    policy = importlib.import_module("root_policy").get_root_evaluator()
    rows = []
    for position in json.loads(args.analysis.read_text())["moves"]:
        remaining = round(position["clock_before_s"] * 1000)
        if not 1200 <= remaining < 6000 or position["loss_cp"] < 150:
            continue
        for mode in ("normal", "uncapped"):
            board = chess.Board(position["fen"])
            player = engine.MilkyWayEngine()
            legal = sorted(board.legal_moves, key=lambda m: m.uci())
            budget = tm.allocate_time(remaining, len(legal))
            clock = tm.Clock()
            clock.start_move(budget)
            scores = policy.get_move_scores(board, legal) if policy.is_available() else {}
            player.searcher.new_search(clock, budget.emergency, root_policy_scores=scores)
            # Keep emergency pruning and check-extension behavior unchanged; remove only
            # the iteration cap through an offline subclass-style method replacement.
            if mode == "uncapped":
                source = importlib.import_module("search")
                import inspect
                import textwrap
                code = textwrap.dedent(inspect.getsource(source.Searcher.iterative_deepening))
                code = code.replace("if self._emergency and depth >= 4:",
                                    "if False and depth >= 4:")
                namespace = dict(vars(source))
                exec(compile(code, "<offline iteration-cap ablation>", "exec"), namespace)
                import types
                player.searcher.iterative_deepening = types.MethodType(
                    namespace["iterative_deepening"], player.searcher)
            move, score, _ = player.searcher.iterative_deepening(
                board, 4 if mode == "normal" else 64, legal[0])
            rows.append({"ply": position["ply"], "mode": mode, "move": move.uci(),
                         "oracle_best": position["best"], "score": score,
                         "depth": player.searcher.stats.depth_reached,
                         "elapsed_ms": clock.elapsed_ms(), "soft_ms": budget.soft_ms,
                         "hard_ms": budget.hard_ms, "remaining_ms": remaining})
            print(json.dumps(rows[-1]), flush=True)
    args.out.write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
