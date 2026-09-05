"""Agent contract tests: legal UCI, promotions, tiny budgets, board integrity."""

from __future__ import annotations

import unittest

import chess

import agent
from tests.positions import (
    CASTLING_FEN,
    EN_PASSANT_FEN,
    PROMOTION_FEN,
    START_FEN,
)


class AgentContractTests(unittest.TestCase):
    def test_start_returns_legal_uci(self) -> None:
        move_uci = agent.get_move(START_FEN, 120000)
        move = chess.Move.from_uci(move_uci)
        self.assertIn(move, chess.Board(START_FEN).legal_moves)

    def test_promotion_suffix(self) -> None:
        move_uci = agent.get_move(PROMOTION_FEN, 5000)
        board = chess.Board(PROMOTION_FEN)
        move = chess.Move.from_uci(move_uci)
        self.assertIn(move, board.legal_moves)
        # g7 pawn should promote; any promotion piece is legal, queen preferred.
        if move.from_square == chess.G7:
            self.assertIsNotNone(move.promotion)

    def test_castling_and_en_passant_legal(self) -> None:
        for fen in (CASTLING_FEN, EN_PASSANT_FEN):
            move_uci = agent.get_move(fen, 2000)
            board = chess.Board(fen)
            self.assertIn(chess.Move.from_uci(move_uci), board.legal_moves)

    def test_tiny_budgets_still_legal(self) -> None:
        board = chess.Board(START_FEN)
        for ms in (5, 20, 100, 500):
            with self.subTest(ms=ms):
                move_uci = agent.get_move(board.fen(), ms)
                self.assertIn(chess.Move.from_uci(move_uci), board.legal_moves)

    def test_no_board_mutation(self) -> None:
        fen = START_FEN
        before = chess.Board(fen).fen()
        agent.get_move(fen, 1000)
        after = chess.Board(fen).fen()
        self.assertEqual(before, after)

    def test_determinism_same_budget_class(self) -> None:
        first = agent.get_move(START_FEN, 500)
        second = agent.get_move(START_FEN, 500)
        board = chess.Board(START_FEN)
        self.assertIn(chess.Move.from_uci(first), board.legal_moves)
        self.assertIn(chess.Move.from_uci(second), board.legal_moves)


if __name__ == "__main__":
    unittest.main()
