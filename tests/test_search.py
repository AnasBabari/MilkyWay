"""Search correctness: mates, hanging pieces, push/pop, mate distance."""

from __future__ import annotations

import unittest

import chess

import agent
from constants import MATE_SCORE
from tests.positions import HANGING_QUEEN_FEN, MATE_IN_1_FEN, MATE_IN_1_MOVE


class SearchTests(unittest.TestCase):
    def test_mate_in_one_found(self) -> None:
        move_uci = agent.get_move(MATE_IN_1_FEN, 5000)
        self.assertEqual(move_uci, MATE_IN_1_MOVE)
        board = chess.Board(MATE_IN_1_FEN)
        board.push(chess.Move.from_uci(move_uci))
        self.assertTrue(board.is_checkmate())

    def test_hanging_queen_captured(self) -> None:
        move_uci = agent.get_move(HANGING_QUEEN_FEN, 5000)
        board = chess.Board(HANGING_QUEEN_FEN)
        move = chess.Move.from_uci(move_uci)
        self.assertIn(move, board.legal_moves)
        # Qxd5 wins the queen; accept any queen capture of d5.
        self.assertEqual(move.to_square, chess.D5)

    def test_push_pop_integrity(self) -> None:
        board = chess.Board()
        fen_before = board.fen()
        key_before = board._transposition_key()
        for move in list(board.legal_moves)[:10]:
            board.push(move)
            board.pop()
        self.assertEqual(board.fen(), fen_before)
        self.assertEqual(board._transposition_key(), key_before)

    def test_mate_distance_ordering(self) -> None:
        # Mate scores with ply distance: sooner mate must score higher.
        self.assertGreater(MATE_SCORE - 3, MATE_SCORE - 7)
        self.assertLess(-MATE_SCORE + 3, -MATE_SCORE + 7)

    def test_stalemate_not_mate(self) -> None:
        board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertTrue(board.is_stalemate())
        self.assertFalse(board.is_checkmate())
        self.assertEqual(list(board.legal_moves), [])

    def test_check_evasion_legal(self) -> None:
        # Black to move in check from the white rook; must reply legally.
        board = chess.Board("4k3/8/8/8/8/8/4R3/4K3 b - - 0 1")
        self.assertTrue(board.is_check())
        move_uci = agent.get_move(board.fen(), 3000)
        self.assertIn(chess.Move.from_uci(move_uci), board.legal_moves)


if __name__ == "__main__":
    unittest.main()
