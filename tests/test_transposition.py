"""Transposition-table tests: bounds, replacement, generations."""

from __future__ import annotations

import unittest

import chess

from constants import EXACT, LOWER, UPPER
from transposition import TranspositionTable


class TranspositionTests(unittest.TestCase):
    def test_store_and_probe(self) -> None:
        tt = TranspositionTable(max_entries=16)
        board = chess.Board()
        key = board._transposition_key()
        move = chess.Move.from_uci("e2e4")
        tt.store(key, 3, 42, EXACT, move)
        entry = tt.probe(key)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.depth, 3)
        self.assertEqual(entry.score, 42)
        self.assertEqual(entry.bound, EXACT)
        self.assertEqual(entry.best_move, move)

    def test_bounds_preserved(self) -> None:
        tt = TranspositionTable(max_entries=16)
        board = chess.Board()
        key = board._transposition_key()
        tt.store(key, 2, 10, LOWER, None)
        entry = tt.probe(key)
        assert entry is not None
        self.assertEqual(entry.bound, LOWER)
        tt.store("other", 2, -5, UPPER, None)
        other = tt.probe("other")
        assert other is not None
        self.assertEqual(other.bound, UPPER)

    def test_deeper_replaces_shallower(self) -> None:
        tt = TranspositionTable(max_entries=16)
        tt.store("k", 1, 10, UPPER, None)
        tt.store("k", 4, 20, EXACT, None)
        entry = tt.probe("k")
        assert entry is not None
        self.assertEqual(entry.depth, 4)
        self.assertEqual(entry.score, 20)

    def test_bounded_size(self) -> None:
        tt = TranspositionTable(max_entries=8)
        for i in range(50):
            tt.store(f"key-{i}", 1, i, EXACT, None)
        self.assertLessEqual(tt.size, 8)

    def test_generation_ages(self) -> None:
        tt = TranspositionTable(max_entries=16)
        tt.store("k", 1, 1, EXACT, None)
        first_gen = tt.generation
        tt.new_generation()
        self.assertEqual(tt.generation, first_gen + 1)


if __name__ == "__main__":
    unittest.main()
