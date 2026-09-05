"""Differential test: current evaluation vs frozen versions/mw_0_2 or mw_0_1.

Integer math must match EXACTLY on every position. Any mismatch is a
behavior change that needs arena validation, not a pure refactor.
"""

from __future__ import annotations

import argparse
import importlib.util
import random
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constants import MW_0_2_EVAL  # noqa: E402
from evaluation import evaluate as new_evaluate  # noqa: E402


def load_mw_0_2_evaluate() -> Callable[[chess.Board], int]:
    frozen_dir = ROOT / "versions" / "mw_0_2"
    # To ensure imports inside frozen evaluation resolve to versions/mw_0_2:
    spec_c = importlib.util.spec_from_file_location("mw02_constants", frozen_dir / "constants.py")
    if spec_c is None or spec_c.loader is None:
        raise RuntimeError("Could not load mw_0_2 constants")
    mod_c = importlib.util.module_from_spec(spec_c)
    sys.modules["constants"] = mod_c
    spec_c.loader.exec_module(mod_c)

    spec_e = importlib.util.spec_from_file_location("mw02_eval", frozen_dir / "evaluation.py")
    if spec_e is None or spec_e.loader is None:
        raise RuntimeError("Could not load mw_0_2 evaluation")
    mod_e = importlib.util.module_from_spec(spec_e)
    spec_e.loader.exec_module(mod_e)

    # Restore current constants in sys.modules
    spec_curr = importlib.util.spec_from_file_location("constants", ROOT / "constants.py")
    if spec_curr and spec_curr.loader:
        mod_curr = importlib.util.module_from_spec(spec_curr)
        sys.modules["constants"] = mod_curr
        spec_curr.loader.exec_module(mod_curr)

    eval_fn: Callable[[chess.Board], int] = mod_e.evaluate
    return eval_fn


def load_commit_evaluate(commit: str) -> Callable[[chess.Board], int]:
    src = subprocess.run(
        ["git", "show", f"{commit}:evaluation.py"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    consts = subprocess.run(
        ["git", "show", f"{commit}:constants.py"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="mw_diff_"))
    (tmp / "constants.py").write_text(consts, encoding="utf-8")
    (tmp / "old_evaluation.py").write_text(src, encoding="utf-8")
    sys.path.insert(0, str(tmp))
    import old_evaluation  # type: ignore[import-not-found]

    eval_fn: Callable[[chess.Board], int] = old_evaluation.evaluate
    return eval_fn


def random_fen(rng: random.Random, max_plies: int) -> str:
    board = chess.Board()
    for _ in range(rng.randint(0, max_plies)):
        moves = list(board.legal_moves)
        if not moves or board.is_game_over():
            break
        board.push(rng.choice(moves))
    for _ in range(8):
        if not board.is_game_over() and list(board.legal_moves):
            return board.fen()
        if not board.move_stack:
            return chess.STARTING_FEN
        board.pop()
    return chess.STARTING_FEN


def main() -> None:
    parser = argparse.ArgumentParser(description="Differential evaluation test.")
    parser.add_argument("--against", default="mw_0_2", help="mw_0_2, mw_0_1, or git commit")
    parser.add_argument("--positions", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=99)
    args = parser.parse_args()

    if args.against == "mw_0_2":
        old_evaluate = load_mw_0_2_evaluate()
    elif args.against == "mw_0_1":
        old_evaluate = load_commit_evaluate("772e9a5")
    else:
        old_evaluate = load_commit_evaluate(args.against)

    rng = random.Random(args.seed)
    mismatches = 0
    for i in range(args.positions):
        fen = random_fen(rng, 90)
        board = chess.Board(fen)
        old: int = old_evaluate(board)
        new: int = new_evaluate(board, MW_0_2_EVAL)
        if old != new:
            mismatches += 1
            if mismatches <= 10:
                print(f"[{i}] MISMATCH old={old} new={new} fen={fen}")
    print(f"Compared {args.positions} positions against {args.against}: {mismatches} mismatches")
    if mismatches:
        raise SystemExit(f"PARITY FAILED: {mismatches} eval mismatches")
    print(f"PARITY GATE PASSED: 100% exact match across all {args.positions} positions!")


if __name__ == "__main__":
    main()
