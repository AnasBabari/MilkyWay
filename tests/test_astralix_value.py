"""Regression coverage for WDL logit interpretation before runtime integration."""

from __future__ import annotations

import math
import unittest

from tools.astralix_value_audit import logits_to_cp


class TestWDLLogits(unittest.TestCase):
    def test_equal_logits_are_neutral_even_when_negative(self) -> None:
        self.assertEqual(logits_to_cp([-3.0, -3.0, -3.0]), 0.0)

    def test_common_offset_does_not_change_value(self) -> None:
        logits = [-0.17, -0.19, -0.02]
        for offset in (-1000.0, 0.0, 1000.0):
            self.assertAlmostEqual(
                logits_to_cp(logits), logits_to_cp([x + offset for x in logits]), places=8
            )

    def test_win_loss_exchange_reverses_sign(self) -> None:
        value = logits_to_cp([4.0, 1.0, -2.0])
        self.assertGreater(value, 0)
        self.assertAlmostEqual(value, -logits_to_cp([-2.0, 1.0, 4.0]))

    def test_extreme_logits_are_finite(self) -> None:
        self.assertTrue(math.isfinite(logits_to_cp([10000.0, 0.0, -10000.0])))

    def test_invalid_logits_are_rejected(self) -> None:
        for logits in ([0.0], [0.0, 0.0, float("nan")], [float("inf"), 0.0, 0.0]):
            with self.assertRaises(ValueError):
                logits_to_cp(logits)


if __name__ == "__main__":
    unittest.main()
