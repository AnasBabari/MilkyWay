"""Test verifying byte-deterministic packaging (Requirement 11)."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from harness.package import build

ROOT = Path(__file__).resolve().parent.parent


class TestPackageDeterminism(unittest.TestCase):
    def test_package_twice_identical_sha(self) -> None:
        """Building package twice must produce bit-identical zip SHA-256."""
        with tempfile.TemporaryDirectory() as td:
            tpath = Path(td)
            z1 = tpath / "build1.zip"
            z2 = tpath / "build2.zip"

            build(ROOT, z1, ("weights",))
            sha1 = hashlib.sha256(z1.read_bytes()).hexdigest()

            build(ROOT, z2, ("weights",))
            sha2 = hashlib.sha256(z2.read_bytes()).hexdigest()

            self.assertEqual(
                sha1,
                sha2,
                f"Packaging is non-deterministic! SHA1: {sha1} != SHA2: {sha2}",
            )


if __name__ == "__main__":
    unittest.main()
