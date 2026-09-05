"""Unit test ensuring search modules remain bit-for-bit identical to MW-0.2."""

from __future__ import annotations

import unittest

from tools.verify_search_freeze import verify_search_freeze


class TestSearchFreeze(unittest.TestCase):
    def test_search_modules_frozen(self) -> None:
        results = verify_search_freeze()
        for filename, ok in results.items():
            with self.subTest(file=filename):
                self.assertTrue(
                    ok,
                    f"Search freeze violated! {filename} does not match versions/mw_0_2/{filename}",
                )


if __name__ == "__main__":
    unittest.main()
