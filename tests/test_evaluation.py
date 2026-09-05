"""Evaluation invariants: symmetry, material, mating scores separation."""

from __future__ import annotations

import unittest

import chess

from constants import MATE_SCORE
from evaluation import evaluate, evaluate_white_relative


class EvaluationTests(unittest.TestCase):
    def test_start_position_near_level(self) -> None:
        score = evaluate(chess.Board())
        self.assertLess(abs(score), 80)

    def test_material_advantage_positive(self) -> None:
        # White up a queen with kings present.
        board = chess.Board("4k3/8/8/8/8/8/5Q2/4K3 w - - 0 1")
        self.assertGreater(evaluate_white_relative(board), 700)

    def test_stm_symmetry(self) -> None:
        board = chess.Board()
        white_rel = evaluate_white_relative(board)
        stm = evaluate(board)
        self.assertEqual(stm, white_rel)  # white to move
        board.turn = chess.BLACK
        self.assertEqual(evaluate(board), -white_rel)

    def test_mirrored_position_symmetry(self) -> None:
        board = chess.Board("4k3/8/8/3P4/8/8/8/4K3 w - - 0 1")
        mirrored = board.mirror()
        self.assertEqual(evaluate_white_relative(board), -evaluate_white_relative(mirrored))

    def test_eval_far_from_mate(self) -> None:
        board = chess.Board("4k3/8/8/8/8/8/5Q2/4K3 w - - 0 1")
        self.assertLess(abs(evaluate(board)), MATE_SCORE - 10000)

    def test_bishop_pair_bonus(self) -> None:
        two_bishops = chess.Board("4k3/8/8/8/8/8/8/4KB1B w - - 0 1")
        one_bishop = chess.Board("4k3/8/8/8/8/8/8/4KB2 w - - 0 1")
        self.assertGreater(
            evaluate_white_relative(two_bishops), evaluate_white_relative(one_bishop)
        )


if __name__ == "__main__":
    unittest.main()
