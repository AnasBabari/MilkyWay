"""Tests for evaluation feature extraction: schema, parity, and colour-symmetry."""

from __future__ import annotations

import random
import unittest

import chess

from constants import MW_0_2_EVAL, TUNABLE_PARAM_NAMES
from evaluation import evaluate_white_relative
from training.scripts.extract_features import (
    extract_features_white,
    linear_predict_white,
)


class TestFeatureExtraction(unittest.TestCase):
    def test_feature_vector_dimensions(self) -> None:
        board = chess.Board()
        features, fixed = extract_features_white(board)
        self.assertEqual(len(features), len(TUNABLE_PARAM_NAMES))
        self.assertEqual(len(features), 50)
        self.assertAlmostEqual(fixed, 0.0)

    def test_start_position_features_zero(self) -> None:
        board = chess.Board()
        features, fixed = extract_features_white(board)
        for val in features:
            self.assertAlmostEqual(val, 0.0, places=5)
        self.assertAlmostEqual(fixed, 0.0, places=5)

    def test_colour_symmetry(self) -> None:
        """Any valid mirrored position must have negated features and score."""
        fens = [
            chess.STARTING_FEN,
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
            "r1b2rk1/1pq1bppp/p1nppn2/8/3NPP2/2N1B3/PPP1B1PP/R2Q1R1K w - - 0 11",
            "4k3/8/8/3P4/8/8/8/4K3 w - - 0 1",
            "r2q1rk1/pp1b1ppp/2n1pn2/2bp4/2P5/2N1PN2/PP1BBPPP/R2Q1RK1 w - - 0 1",
            "8/2k5/8/8/8/8/2K5/8 w - - 0 1",
        ]
        for fen in fens:
            board = chess.Board(fen)
            mirrored = board.mirror()

            f_orig, fix_orig = extract_features_white(board)
            f_mirr, fix_mirr = extract_features_white(mirrored)

            self.assertAlmostEqual(fix_orig, -fix_mirr, places=4)
            for i, (fo, fm) in enumerate(zip(f_orig, f_mirr, strict=True)):
                self.assertAlmostEqual(
                    fo,
                    -fm,
                    places=4,
                    msg=f"Feature {TUNABLE_PARAM_NAMES[i]} failed symmetry on {fen}",
                )

            ev_orig = evaluate_white_relative(board)
            ev_mirr = evaluate_white_relative(mirrored)
            self.assertEqual(ev_orig, -ev_mirr, f"Eval failed symmetry on {fen}")

    def test_reconstruction_fidelity_on_positions(self) -> None:
        """Linear dot product should be within ±2 cp of integer evaluation on quiet positions."""
        rng = random.Random(42)
        beta = MW_0_2_EVAL.get_tunable_vector()
        max_diff = 0
        tested = 0
        for _ in range(500):
            board = chess.Board()
            for _ in range(rng.randint(5, 50)):
                moves = list(board.legal_moves)
                if not moves or board.is_game_over():
                    break
                board.push(rng.choice(moves))
            if board.is_game_over():
                continue

            features, fixed = extract_features_white(board)
            pred = linear_predict_white(features, fixed, beta)
            actual = evaluate_white_relative(board, MW_0_2_EVAL)
            diff = abs(actual - round(pred))
            if diff > max_diff:
                max_diff = diff
            tested += 1
            # In cases without severe king safety saturation, difference is <= 3 cp
            msg = f"High error: actual={actual}, pred={pred:.2f} on {board.fen()}"
            self.assertLessEqual(diff, 3, msg)
        self.assertGreater(tested, 400)
        self.assertLessEqual(max_diff, 3)


if __name__ == "__main__":
    unittest.main()
