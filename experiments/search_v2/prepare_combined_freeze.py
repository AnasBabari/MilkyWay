"""Freeze the combined staged+LMR variant after verification, or explain why not.

Usage: python prepare_combined_freeze.py

Refuses to write combined_freeze_manifest.json unless combined_verification_01.json
exists with verified=true. Copies nothing; the tournament controller freezes on
its next start. Never edits frozen runtimes or the parent.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "combined_interface_runtime"
VERIFICATION = HERE / "combined_verification_01.json"
MANIFEST = HERE / "combined_freeze_manifest.json"

RUNTIME_FILES = [
    "agent.py",
    "combined_search.py",
    "compact_value.py",
    "compiled_eval.py",
    "compiled_search.py",
    "constants.py",
    "core.py",
    "evaluation.py",
    "fast_eval.py",
    "ordered_search.py",
    "time_manager.py",
    "weights/compact_value.npz",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if MANIFEST.exists():
        print("combined_freeze_manifest.json already exists; nothing to do.")
        return 0
    if not VERIFICATION.exists():
        print("verification has not run yet; refusing to freeze.")
        return 1
    verification = json.loads(VERIFICATION.read_text(encoding="utf-8-sig"))
    if not verification.get("verified"):
        print("verification did not pass; refusing to freeze.")
        return 2
    digests = {name: sha(RUNTIME / name) for name in RUNTIME_FILES}
    MANIFEST.write_text(json.dumps(
        {
            "mechanism": "staged_lmr_combined",
            "source_runtime": str(RUNTIME),
            "verification": "combined_verification_01.json",
            "verification_summary": {
                "total_reductions": verification.get("total_reductions"),
                "total_reduction_researches": verification.get(
                    "total_reduction_researches"),
                "nodes_combo": verification.get("nodes_combo"),
                "nodes_baseline": verification.get("nodes_baseline"),
                "disagreements": len(verification.get("disagreements", [])),
                "worst_disagreement_delta_cp": verification.get(
                    "worst_disagreement_delta_cp"),
                "low_clock_failures": verification.get("low_clock_failures"),
                "selfplay_legal": verification.get("selfplay_legal"),
            },
            "sha256": digests,
        },
        indent=2,
    ) + "\n")
    print("combined_freeze_manifest.json written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())