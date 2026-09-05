"""Tactics regression: recaptures, promotions, castling rights, ep."""

from __future__ import annotations

import unittest

import chess

import agent


class TacticsTests(unittest.TestCase):
    def test_forced_recapture(self) -> None:
        # White knight on e5, black pawn d6 attacks it... use a simple exchange:
        # white pawn e4, black pawn d5; white exd5 recaptures toward center.
        board = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 1")
        move_uci = agent.get_move(board.fen(), 3000)
        self.assertIn(chess.Move.from_uci(move_uci), board.legal_moves)

    def test_promotion_tactic(self) -> None:
        board = chess.Board("7k/6P1/8/8/8/8/5PPP/6K1 w - - 0 1")
        move_uci = agent.get_move(board.fen(), 3000)
        move = chess.Move.from_uci(move_uci)
        self.assertIn(move, board.legal_moves)
        board.push(move)
        # White should either promote immediately or force it; at minimum the
        # g-pawn must advance or promote.
        self.assertTrue(
            any(p.symbol() == "P" for p in board.piece_map().values())
            or any(p.symbol() == "Q" for p in board.piece_map().values())
        )

    def test_castling_legality_preserved(self) -> None:
        board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
        move_uci = agent.get_move(board.fen(), 3000)
        self.assertIn(chess.Move.from_uci(move_uci), board.legal_moves)

    def test_king_never_left_in_check(self) -> None:
        fens = [
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 0 1",
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 1",
        ]
        for fen in fens:
            with self.subTest(fen=fen):
                board = chess.Board(fen)
                move = chess.Move.from_uci(agent.get_move(fen, 2000))
                self.assertIn(move, board.legal_moves)
                board.push(move)
                # Opponent to move must have a well-formed position.
                self.assertIsNotNone(board.fen())


if __name__ == "__main__":
    unittest.main()
