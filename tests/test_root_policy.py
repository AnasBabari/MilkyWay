"""Unit tests for MilkyWay M17 single-core CPU root policy evaluator and move ordering."""

from __future__ import annotations

import os
import unittest

import chess

from engine import MilkyWayEngine
from move_ordering import order_root_moves
from root_policy import RootPolicyEvaluator, get_root_evaluator


class TestRootPolicy(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = get_root_evaluator()

    def test_evaluator_availability(self) -> None:
        self.assertTrue(self.evaluator.is_available(), "Root policy model should be available")

    def test_get_move_scores_startpos(self) -> None:
        board = chess.Board()
        legal_moves = list(board.legal_moves)
        scores = self.evaluator.get_move_scores(board, legal_moves)

        self.assertEqual(len(scores), len(legal_moves))
        for m in legal_moves:
            self.assertIn(m, scores)
            self.assertIsInstance(scores[m], float)

    def test_get_move_scores_empty_legal_moves(self) -> None:
        board = chess.Board()
        scores = self.evaluator.get_move_scores(board, [])
        self.assertEqual(scores, {})

    def test_evaluator_disabled_by_env(self) -> None:
        old_env = os.environ.get("MILKYWAY_ROOT_POLICY")
        try:
            os.environ["MILKYWAY_ROOT_POLICY"] = "0"
            disabled_evaluator = RootPolicyEvaluator()
            self.assertFalse(disabled_evaluator.is_available())
            self.assertEqual(
                disabled_evaluator.get_move_scores(chess.Board(), [chess.Move.from_uci("e2e4")]), {}
            )
        finally:
            if old_env is not None:
                os.environ["MILKYWAY_ROOT_POLICY"] = old_env
            else:
                os.environ.pop("MILKYWAY_ROOT_POLICY", None)

    def test_order_root_moves_tt_move_first(self) -> None:
        board = chess.Board()
        moves = list(board.legal_moves)
        tt_move = chess.Move.from_uci("e2e4")
        policy_scores = {m: 0.0 for m in moves}
        policy_scores[chess.Move.from_uci("d2d4")] = 20.0

        history = [[[0 for _ in range(64)] for _ in range(64)] for _ in range(2)]
        ordered = order_root_moves(board, moves, tt_move, policy_scores, history)

        self.assertEqual(ordered[0], tt_move, "TT move must always be ordered first at root")

    def test_order_root_moves_captures_precede_quiets(self) -> None:
        fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
        board = chess.Board(fen)
        moves = list(board.legal_moves)
        capture_move = chess.Move.from_uci("f3e5")
        self.assertTrue(board.is_capture(capture_move))

        quiet_move = chess.Move.from_uci("b1c3")
        policy_scores = {m: -10.0 for m in moves}
        policy_scores[quiet_move] = 10.0
        policy_scores[capture_move] = -5.0

        history = [[[0 for _ in range(64)] for _ in range(64)] for _ in range(2)]
        ordered = order_root_moves(board, moves, None, policy_scores, history)

        idx_capture = ordered.index(capture_move)
        idx_quiet = ordered.index(quiet_move)
        self.assertLess(
            idx_capture,
            idx_quiet,
            f"Capture ({idx_capture}) must precede quiet move ({idx_quiet}) even with high policy",
        )

    def test_order_root_moves_policy_orders_quiets(self) -> None:
        board = chess.Board()
        moves = list(board.legal_moves)
        preferred = chess.Move.from_uci("e2e4")
        disliked = chess.Move.from_uci("a2a3")

        policy_scores = {m: 0.0 for m in moves}
        policy_scores[preferred] = 5.0
        policy_scores[disliked] = -5.0

        history = [[[0 for _ in range(64)] for _ in range(64)] for _ in range(2)]
        ordered = order_root_moves(board, moves, None, policy_scores, history)

        self.assertLess(
            ordered.index(preferred),
            ordered.index(disliked),
            "Preferred policy move must be ordered before disliked move",
        )

    def test_engine_choose_move_end_to_end(self) -> None:
        engine = MilkyWayEngine()
        board = chess.Board()
        move_uci = engine.choose_move(board.fen(), 5000)
        move = chess.Move.from_uci(move_uci)
        self.assertIn(move, board.legal_moves, f"Move {move_uci} must be legal")


if __name__ == "__main__":
    unittest.main()
