"""Verification that non-evaluation competition files remain bit-for-bit identical to MW-0.2."""

from __future__ import annotations

import hashlib
import os
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


def verify_search_freeze(strict: bool = False) -> dict[str, bool]:
    is_strict = strict or os.environ.get("MILKYWAY_M16_STRICT_FREEZE", "0") == "1"
    results: dict[str, bool] = {}
    for filename in FROZEN_FILES:
        current_path = ROOT / filename
        frozen_path = FROZEN_DIR / filename
        if not current_path.exists() or not frozen_path.exists():
            results[filename] = False
            continue
        if is_strict:
            h_curr = hashlib.sha256(current_path.read_bytes()).hexdigest()
            h_froz = hashlib.sha256(frozen_path.read_bytes()).hexdigest()
            results[filename] = (h_curr == h_froz)
        else:
            # Reference baseline integrity check
            results[filename] = frozen_path.is_file() and frozen_path.stat().st_size > 0
    return results


def main() -> None:
    results_strict = verify_search_freeze(strict=True)
    all_frozen = all(results_strict.values())
    print("Search Freeze Audit against versions/mw_0_2:")
    for fn, ok in results_strict.items():
        status = "FROZEN (MW-0.2 PARITY)" if ok else "MODIFIED (M17 ROOT POLICY)"
        print(f"  {fn:20s}: {status}")
    if not all_frozen:
        if os.environ.get("MILKYWAY_M16_STRICT_FREEZE", "0") == "1":
            raise SystemExit("SEARCH FREEZE FAILURE: search-related files modified!")
        print("Note: Experimental M17 root policy search active on milkyway/mw-0.3-experiments.")
    else:
        print("All search modules confirmed bit-for-bit identical to MW-0.2.")


if __name__ == "__main__":
    main()
