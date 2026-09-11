"""Regression checks for offline oracle scoring and submission isolation."""
from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import chess
import chess.engine

from baselines.stockfish import agent as stockfish
from harness.package import members
from tools.measure_acpl import (
    ACPL_TEST_SUITE,
    evaluate_agent_acpl,
    measure_move_loss,
    score_to_cp,
)


class StockfishIntegrationTests(unittest.TestCase):
    def test_bank_valid_balanced_unique(self) -> None:
        from collections import Counter

        self.assertEqual(Counter(p.category for p in ACPL_TEST_SUITE),
                         dict.fromkeys(("opening", "tactical", "middlegame", "endgame"), 25))
        self.assertEqual(len({p.fen for p in ACPL_TEST_SUITE}), 100)
        for pos in ACPL_TEST_SUITE:
            board = chess.Board(pos.fen)
            self.assertTrue(board.is_valid(), pos.id)
            self.assertFalse(board.is_game_over(), pos.id)

    def test_caps_scores_before_subtraction(self) -> None:
        board = chess.Board()
        oracle = MagicMock()
        oracle.analyse.side_effect = [
            {"score": chess.engine.PovScore(chess.engine.Cp(8000), chess.WHITE),
             "pv": [chess.Move.from_uci("e2e4")]},
            {"score": chess.engine.PovScore(chess.engine.Cp(2000), chess.WHITE)},
        ]
        result = measure_move_loss(oracle, board, chess.Move.from_uci("d2d4"))
        self.assertEqual(result["cpl"], 0)
        self.assertEqual(oracle.analyse.call_args.kwargs["root_moves"],
                         [chess.Move.from_uci("d2d4")])
        self.assertEqual(board.fen(), chess.STARTING_FEN)

    def test_black_pov_and_mates(self) -> None:
        score = chess.engine.PovScore(chess.engine.Cp(230), chess.WHITE)
        self.assertEqual(score_to_cp(score, chess.BLACK), -230)
        mate = chess.engine.PovScore(chess.engine.Mate(1), chess.BLACK)
        self.assertEqual(score_to_cp(mate, chess.BLACK), 1000)
        self.assertEqual(score_to_cp(mate, chess.WHITE), -1000)

    def test_illegal_move_is_error(self) -> None:
        with self.assertRaises(ValueError):
            measure_move_loss(MagicMock(), chess.Board(), chess.Move.from_uci("e2e5"))

    def test_custom_target_and_disjoint_boundaries(self) -> None:
        losses = [0, 50, 100, 200, 201]
        oracle = MagicMock()
        with patch("tools.measure_acpl.find_stockfish_binary", return_value="sf"), patch(
            "tools.measure_acpl.chess.engine.SimpleEngine.popen_uci",
            return_value=oracle,
        ), patch("tools.measure_acpl.measure_move_loss",
                 side_effect=[{"cpl": c} for c in losses]):
            result = evaluate_agent_acpl(
                SimpleNamespace(get_move=lambda fen, budget: "e2e4"),
                (ACPL_TEST_SUITE[0],) * 5, target=120,
            )
        self.assertTrue(result["passed_target"])
        self.assertEqual(result["target_acpl"], 120)
        counts = result["distribution"]
        self.assertEqual([counts[k] for k in (
            "best_moves_count", "good_moves_count", "inaccuracies_count",
            "mistakes_count", "blunders_count",
        )], [1, 1, 1, 1, 1])
        oracle.__exit__.assert_called_once()

    def test_empty_bank_fails(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_agent_acpl(MagicMock(), ())

    def test_missing_stockfish_does_not_become_random(self) -> None:
        with patch.object(stockfish, "_ENGINE", None), patch.object(
            stockfish, "find_stockfish_binary", return_value=None,
        ), self.assertRaises(FileNotFoundError):
            stockfish.get_move(chess.STARTING_FEN, 5000)

    def test_invalid_explicit_binary_fails(self) -> None:
        with patch.dict("os.environ", {"STOCKFISH_PATH": "missing-sf"}), patch(
            "shutil.which", return_value=None,
        ), self.assertRaises(FileNotFoundError):
            stockfish.find_stockfish_binary()

    def test_default_submission_excludes_offline_tools(self) -> None:
        root = Path(__file__).resolve().parents[1]
        names = [name.replace("\\", "/") for _, name in members(root, ("weights",))]
        self.assertIn("agent.py", names)
        self.assertFalse(any("stockfish" in n.lower() for n in names))
        self.assertFalse(any(n.startswith(("tools/", "training/", "baselines/")) for n in names))


if __name__ == "__main__":
    unittest.main()
