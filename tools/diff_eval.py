"""Differential test: current evaluation vs MW-0.1 (commit 772e9a5).

Integer math must match EXACTLY on every position. Any mismatch is a
behavior change that needs arena validation, not a pure optimisation.
"""

import random
import subprocess
import sys
import tempfile
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation import evaluate as new_evaluate  # noqa: E402


def load_old_evaluate() -> object:
    src = subprocess.run(
        ["git", "show", "772e9a5:evaluation.py"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    consts = subprocess.run(
        ["git", "show", "772e9a5:constants.py"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="mw01_"))
    (tmp / "constants.py").write_text(consts, encoding="utf-8")
    (tmp / "old_evaluation.py").write_text(src, encoding="utf-8")
    sys.path.insert(0, str(tmp))
    import old_evaluation  # type: ignore[import-not-found]

    return old_evaluation.evaluate


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
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--positions", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=99)
    args = parser.parse_args()

    old_evaluate = load_old_evaluate()
    rng = random.Random(args.seed)
    mismatches = 0
    for i in range(args.positions):
        fen = random_fen(rng, 90)
        board = chess.Board(fen)
        old = old_evaluate(board)  # type: ignore[operator]
        new = new_evaluate(board)
        if old != new:
            mismatches += 1
            if mismatches <= 10:
                print(f"[{i}] MISMATCH old={old} new={new} fen={fen}")
    print(f"compared {args.positions} positions, {mismatches} mismatches")
    if mismatches:
        raise SystemExit(f"{mismatches} eval mismatches")


if __name__ == "__main__":
    main()
