"""Measure loss of neural ordering distinctions from absolute logit clipping."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "experiments/silky_snow"))
    policy = importlib.import_module("root_policy")
    sys.path.append(str(root))
    from training.data.representation import tensor_to_board

    with np.load(root / "training/datasets/master_value_v2/val/shard_00000.npz") as data:
        positions = data["boards"][:256]
    reports = []
    for name in ("experiments/silky_snow/weights/milkyway_policy.onnx",
                 "weights/milkyway_flagship_v6.onnx"):
        evaluator = policy.RootPolicyEvaluator(root / name)
        assert evaluator.is_available()
        total = clipped = tied_top = valid = 0
        for tensor in positions:
            board = tensor_to_board(tensor)
            moves = [m for m in board.legal_moves if not board.is_capture(m) and not m.promotion]
            if len(moves) < 2:
                continue
            scores = list(evaluator.get_move_scores(board, moves).values())
            assert len(scores) == len(moves)
            total += len(scores)
            clipped += sum(abs(s) >= 5 for s in scores)
            bounded = [max(-5, min(5, s)) for s in scores]
            tied_top += sum(s == max(bounded) for s in bounded) > 1
            valid += 1
        reports.append({"model": name, "positions": valid, "quiet_scores": total,
                        "clipped_fraction": clipped / total, "top_tie_positions": tied_top})
    (root / "experiments/compact_cycle_01/policy_clipping.json").write_text(
        json.dumps(reports, indent=2))
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
