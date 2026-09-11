"""Audit exported WDL logits without changing frozen runtime behavior."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from pathlib import Path

import chess
import numpy as np


def logits_to_cp(logits: list[float]) -> float:
    if len(logits) != 3 or not all(math.isfinite(x) for x in logits):
        raise ValueError("Expected three finite WDL logits")
    peak = max(logits)
    weights = [math.exp(x - peak) for x in logits]
    total = sum(weights)
    expected = (weights[0] + 0.5 * weights[1]) / total
    expected = min(0.999, max(0.001, expected))
    return 400.0 * math.log10(expected / (1.0 - expected))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.agent.resolve()))
    runtime = importlib.import_module("root_policy")
    evaluator = runtime.get_root_evaluator()
    assert evaluator.is_available()
    assert evaluator.session is not None
    checks = []
    for logits in ([0., 0., 0.], [3., 0., -3.], [-3., 0., 3.], [1000., 999., 998.]):
        cp = logits_to_cp(logits)
        assert abs(cp - logits_to_cp([x + 500 for x in logits])) < 1e-9
        assert abs(cp + logits_to_cp(list(reversed(logits)))) < 1e-8
        checks.append({"logits": logits, "cp": cp})
    assert logits_to_cp([3., 0., -3.]) > 0
    assert logits_to_cp([-3., 0., 3.]) < 0
    positions = {
        "start": chess.STARTING_FEN,
        "white_queen_white_turn": "4k3/8/8/8/8/8/Q7/4K3 w - - 0 1",
        "white_queen_black_turn": "4k3/8/8/8/8/8/Q7/4K3 b - - 0 1",
        "black_queen_white_turn": "4k3/q7/8/8/8/8/8/4K3 w - - 0 1",
        "black_queen_black_turn": "4k3/q7/8/8/8/8/8/4K3 b - - 0 1",
    }
    records = []
    for name, fen in positions.items():
        board = chess.Board(fen)
        assert board.is_valid(), name
        raw = evaluator.session.run(
            [evaluator.value_name],
            {evaluator.input_name: np.expand_dims(
                runtime.board_to_tensor(board).astype(np.float32), 0
            )},
        )[0][0]
        logits = [float(x) for x in raw]
        records.append({"name": name, "fen": fen, "logits": logits,
                        "current_cp": evaluator.value_wdl_to_cp(*logits),
                        "corrected_cp": logits_to_cp(logits)})
    args.out.write_text(json.dumps(
        {"conversion_invariants": checks, "positions": records}, indent=2
    ))
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
