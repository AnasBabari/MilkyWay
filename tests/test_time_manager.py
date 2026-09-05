"""Time-manager unit tests: emergency mode, safety margins, single move."""

from __future__ import annotations

import unittest

from time_manager import allocate_time


class TimeManagerTests(unittest.TestCase):
    def test_normal_budget_within_clock(self) -> None:
        budget = allocate_time(120000, 30)
        self.assertGreater(budget.soft_ms, 100)
        self.assertGreater(budget.hard_ms, budget.soft_ms)
        self.assertLess(budget.hard_ms, 120000 - 200)
        self.assertFalse(budget.emergency)

    def test_emergency_on_low_clock(self) -> None:
        budget = allocate_time(800, 30)
        self.assertTrue(budget.emergency)
        self.assertLessEqual(budget.hard_ms, 800)

    def test_single_legal_move_is_fast(self) -> None:
        budget = allocate_time(120000, 1)
        self.assertLessEqual(budget.soft_ms, 60)

    def test_tiny_clock_leaves_margin(self) -> None:
        budget = allocate_time(400, 20)
        self.assertLessEqual(budget.hard_ms, 400)
        self.assertGreaterEqual(budget.hard_ms, 60)

    def test_many_moves_get_more_time(self) -> None:
        few = allocate_time(60000, 5)
        many = allocate_time(60000, 40)
        self.assertGreaterEqual(many.soft_ms, few.soft_ms)


if __name__ == "__main__":
    unittest.main()
