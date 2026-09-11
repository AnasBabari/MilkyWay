"""Controlled fixed-depth evaluation ablation, without modifying frozen agents."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

import chess


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--positions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--coefficient", type=float)
    args = parser.parse_args()
    sys.path.insert(0, str(args.agent.resolve()))
    search = importlib.import_module("search")
    runtime = importlib.import_module("compact_value")
    tm = importlib.import_module("time_manager")
    tt = importlib.import_module("transposition")
    policy = importlib.import_module("root_policy").get_root_evaluator()
    rows = []
    for position in json.loads(args.positions.read_text()):
        coefficients = ((None, 0.0, 0.25, 1.0) if args.coefficient is None
                        else (args.coefficient,))
        for coefficient in coefficients:
            board = chess.Board(position["start_fen"])
            if coefficient is None:
                search.evaluate = runtime.classical_evaluate
            else:
                def evaluation(b: chess.Board, c: float = coefficient) -> int:
                    delta = round(c * runtime.residual_white(b))
                    return runtime.classical_evaluate(b) + (delta if b.turn else -delta)
                search.evaluate = evaluation
            worker = search.Searcher(tt.TranspositionTable(max_entries=524288))
            clock = tm.Clock()
            clock.start_move(tm.TimeBudget(60000, 60000, False))
            legal = sorted(board.legal_moves, key=lambda m: m.uci())
            scores = policy.get_move_scores(board, legal) if policy.is_available() else {}
            worker.new_search(clock, False, root_policy_scores=scores)
            start = time.perf_counter()
            move, value, _ = worker.iterative_deepening(board, args.depth, legal[0])
            assert board.fen() == position["start_fen"], "Search leaked board mutation"
            row = {"position": position["pos_id"], "coefficient": coefficient,
                   "move": move.uci(), "score": value, "depth": worker.stats.depth_reached,
                   "nodes": worker.stats.nodes, "qnodes": worker.stats.qnodes,
                   "seconds": time.perf_counter() - start}
            rows.append(row)
            print(json.dumps(row), flush=True)
    args.out.write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
