"""Regression tests for positions encountered during rated AI Chessathon games."""

from __future__ import annotations

import unittest

import chess

from constants import INF
from time_manager import Clock, TimeBudget
from tools.analyze_position import DiagnosticSearcher
from transposition import TranspositionTable

ROUND20_LARPMAXX_CRITICAL = (
    "1rBq1r2/1p3p1k/2n3pb/p1p4p/P3Pp1P/3P2P1/1PPQ1P2/R2R2K1 w - - 0 19"
)

ROUND20_LARPMAXX_MATE = (
    "1r3r2/1p5k/2np2pb/p1p5/P3P1qP/2NP1p2/1PPQ1P1K/R2R4 w - - 0 23"
)


class TestRatedRegressions(unittest.TestCase):
    def setUp(self) -> None:
        self.tt = TranspositionTable(16)
        self.searcher = DiagnosticSearcher(self.tt)
        self.clock = Clock()
        self.clock.start_move(TimeBudget(soft_ms=1000000.0, hard_ms=1000000.0, emergency=False))

    def test_round20_move23_mate_delay(self) -> None:
        """Position 23: White is facing unstoppable mate in 2.

        Every legal move except Qxh6+ and Qg5 allows immediate 23...Qg2#.
        Verify that search correctly delays mate rather than allowing immediate mate in 1.
        """
        board = chess.Board(ROUND20_LARPMAXX_MATE)
        self.searcher.new_search(self.clock, emergency=False)
        score, pv = self.searcher._search_root(board, 4, -INF, INF)
        self.assertTrue(len(pv) > 0)
        best_uci = pv[0].uci()
        # d2h6 (Qxh6+) and d2g5 (Qg5) are the only moves delaying mate
        self.assertIn(best_uci, ["d2h6", "d2g5"])
        # Score must reflect impending mate (distance-adjusted negative mate score)
        self.assertLess(score, -90000)

    def test_round20_move19_shallow_depth_prefers_bishop_retreat(self) -> None:
        """Position 19: at shallow depths (1-2), Bh3 is preferred over hanging bishop."""
        board = chess.Board(ROUND20_LARPMAXX_CRITICAL)
        for depth in [1, 2]:
            self.tt.clear()
            self.searcher.new_search(self.clock, emergency=False)
            _score, pv = self.searcher._search_root(board, depth, -INF, INF)
            self.assertTrue(len(pv) > 0)
            self.assertEqual(pv[0].uci(), "c8h3")

    def test_round20_move19_unpruned_rejects_g4(self) -> None:
        """Position 19: in conservative/unpruned search, g3g4 is refuted by Nd4! (-967 cp).

        d2c3 is preferred over g3g4.
        """
        board = chess.Board(ROUND20_LARPMAXX_CRITICAL)
        unpruned_searcher = DiagnosticSearcher(
            self.tt,
            enable_lmr=False,
            enable_null=False,
            enable_futility=False,
            enable_rf=False,
        )
        unpruned_searcher.new_search(self.clock, emergency=False)
        _score, pv = unpruned_searcher._search_root(board, 6, -INF, INF)
        self.assertTrue(len(pv) > 0)
        # Unpruned search must NOT choose g3g4
        self.assertNotEqual(pv[0].uci(), "g3g4")
        self.assertEqual(pv[0].uci(), "d2c3")


if __name__ == "__main__":
    unittest.main()
