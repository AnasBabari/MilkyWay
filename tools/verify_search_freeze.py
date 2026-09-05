"""Verification that non-evaluation competition files remain bit-for-bit identical to MW-0.2."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FROZEN_DIR = ROOT / "versions" / "mw_0_2"

FROZEN_FILES = (
    "agent.py",
    "engine.py",
    "engine_types.py",
    "move_ordering.py",
    "search.py",
    "time_manager.py",
    "transposition.py",
)


def verify_search_freeze() -> dict[str, bool]:
    results: dict[str, bool] = {}
    for filename in FROZEN_FILES:
        current_path = ROOT / filename
        frozen_path = FROZEN_DIR / filename
        if not current_path.exists() or not frozen_path.exists():
            results[filename] = False
            continue
        h_curr = hashlib.sha256(current_path.read_bytes()).hexdigest()
        h_froz = hashlib.sha256(frozen_path.read_bytes()).hexdigest()
        results[filename] = (h_curr == h_froz)
    return results


def main() -> None:
    results = verify_search_freeze()
    all_ok = True
    print("Search Freeze Audit against versions/mw_0_2:")
    for fn, ok in results.items():
        status = "FROZEN (OK)" if ok else "MODIFIED (VIOLATION)"
        print(f"  {fn:20s}: {status}")
        if not ok:
            all_ok = False
    if not all_ok:
        raise SystemExit("SEARCH FREEZE FAILURE: search-related files modified!")
    print("All search modules confirmed bit-for-bit identical to MW-0.2.")


if __name__ == "__main__":
    main()
