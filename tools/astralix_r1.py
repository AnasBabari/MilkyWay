"""Prepare and verify an isolated policy-ordering ablation from frozen Astralix v1."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "experiments/astralix"

VERIFY = '''
import json
from unittest.mock import patch
import chess
import engine
import astralix_config
from root_policy import get_root_evaluator
from time_manager import allocate_time

evaluator = get_root_evaluator()
assert evaluator.is_available(), "model must load in both arms"
board = chess.Board()
scores, _ = evaluator.evaluate_root(board, list(board.legal_moves))
assert len(scores) == board.legal_moves.count()
for value in (-1500.0, 0.0, 1500.0):
    eng = engine.MilkyWayEngine()
    eng._last_score = 0
    budget = allocate_time(30000, board.legal_moves.count())
    captured = {}
    def new_search(clock, emergency, root_policy_scores):
        captured.update(soft=(clock.soft_deadline-clock.start)*1000,
                        hard=(clock.hard_deadline-clock.start)*1000,
                        scores=root_policy_scores)
    with patch.object(evaluator, "evaluate_root", return_value=(scores, value)) as infer, \
         patch.object(eng.searcher, "new_search", side_effect=new_search), \
         patch.object(eng.searcher, "iterative_deepening",
                      side_effect=lambda b,d,f: (f,0,[f])):
        move = eng.choose_move(board.fen(), 30000)
    assert infer.call_count == 1
    assert chess.Move.from_uci(move) in board.legal_moves
    assert abs(captured["soft"]-budget.soft_ms) < 0.01
    assert abs(captured["hard"]-budget.hard_ms) < 0.01
    assert captured["scores"] == (scores if astralix_config.POLICY_ORDERING else {})
print(json.dumps({"policy_ordering": astralix_config.POLICY_ORDERING,
                  "module": engine.__file__, "model_available": True,
                  "extreme_value_clock_invariance": True}))
'''


def hashes(directory: Path) -> dict[str, str]:
    files = sorted(directory.glob("*.py")) + sorted((directory / "weights").glob("*.onnx"))
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files}


def main() -> None:
    source = LAB / "v1"
    base_hashes = hashes(source)
    engine = (source / "engine.py").read_text()
    engine = engine.replace("import math\n", "")
    engine = engine.replace("from evaluation import evaluate\n", "")
    engine = engine.replace("from constants import INF, MATE_SCORE\n",
                            "from astralix_config import POLICY_ORDERING\n"
                            "from constants import INF, MATE_SCORE\n")
    start = engine.index(
        "        # Single-core CPU root policy move scores + learned position value."
    )
    end = engine.index("        self.searcher.new_search", start)
    replacement = (
        "        # Both arms perform identical inference; only ordering consumption differs.\n"
        + '''
        # Learned value is discarded. No blend or learned clock scaling is active.
        policy_scores: dict[chess.Move, float] = {}
        try:
            evaluator = get_root_evaluator()
            if evaluator.is_available():
                scores, _ = evaluator.evaluate_root(board, legal_sorted)
                if POLICY_ORDERING:
                    policy_scores = scores
        except Exception:
            policy_scores = {}

'''.lstrip("\n")
    )
    engine = engine[:start] + replacement + engine[end:]
    arms = {}
    for name, enabled in (("r1_policy", True), ("r1_control", False)):
        destination = LAB / name
        expected = {f: (source / f).read_bytes() for f in base_hashes}
        expected["engine.py"] = engine.encode()
        expected["astralix_config.py"] = (
            '"""Frozen R1 configuration: value and time scaling are absent in both arms."""\n'
            f"POLICY_ORDERING: bool = {enabled}\n"
        ).encode()
        if destination.exists():
            if (destination / "engine.py").read_bytes() != expected["engine.py"]:
                import difflib

                print("".join(difflib.unified_diff(
                    (destination / "engine.py").read_text().splitlines(keepends=True),
                    engine.splitlines(keepends=True),
                )))
            assert hashes(destination) == {
                f: hashlib.sha256(data).hexdigest() for f, data in expected.items()
            }, f"Existing variant changed: {destination}"
        else:
            for filename, data in expected.items():
                target = destination / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        result = subprocess.run([sys.executable, "-c", VERIFY], cwd=destination,
                                text=True, capture_output=True, check=True)
        arms[name] = {"hashes": hashes(destination), "checks": json.loads(result.stdout)}
    differences = [f for f, h in arms["r1_policy"]["hashes"].items()
                   if arms["r1_control"]["hashes"].get(f) != h]
    assert differences == ["astralix_config.py"]
    report = {"base_hashes": base_hashes, "arms": arms, "only_differences": differences,
              "protocol": {"pairs": 10, "base_ms": 10000, "increment_ms": 100,
                           "workers": 1, "seed": 20260906, "bank": "screen",
                           "purpose": "diagnostic; no promotion or retraining gate alone"}}
    (LAB / "r1_manifest.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"verified": True, "only_differences": differences}, indent=2))


if __name__ == "__main__":
    main()
