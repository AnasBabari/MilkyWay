"""Run repository regressions against the candidate's runtime modules."""

from __future__ import annotations

import argparse
import importlib
import sys
import unittest
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    repo = args.repo.resolve()
    sys.path[:0] = [str(candidate), str(repo)]
    for name in ("agent", "engine", "search", "evaluation", "time_manager", "root_policy"):
        module = importlib.import_module(name)
        if Path(module.__file__).resolve().parent != candidate:
            raise RuntimeError(f"Tests would import the wrong {name} module")
    print(f"Testing runtime modules from {candidate}", flush=True)
    suite = unittest.defaultTestLoader.discover(str(repo / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
