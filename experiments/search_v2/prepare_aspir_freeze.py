"""Freeze the aspiration variant after verification, or explain why not.

Usage: python prepare_aspir_freeze.py

Refuses to write aspir_freeze_manifest.json unless aspir_verification_01.json
exists with verified=true. Never edits the frozen parent or any runtime.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "aspir_interface_runtime"
VERIFICATION = HERE / "aspir_verification_01.json"
MANIFEST = HERE / "aspir_freeze_manifest.json"

RUNTIME_FILES = [
    "agent.py",
    "aspir_search.py",
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
        print("aspir_freeze_manifest.json already exists; nothing to do.")
        return 0
    if not VERIFICATION.exists():
        print("verification has not run yet; refusing to freeze.")
        return 1
    verification = json.loads(VERIFICATION.read_text(encoding="utf-8-sig"))
    if not verification.get("verified"):
        print(f"verification failed: {verification.get('low_clock_failures')}, "
              f"worst_delta={verification.get('worst_disagreement_delta_cp')}cp; "
              "refusing to freeze.")
        return 2
    digests = {name: sha(RUNTIME / name) for name in RUNTIME_FILES}
    MANIFEST.write_text(json.dumps(
        {
            "mechanism": "aspiration",
            "aspiration_delta_cp": 45,
            "source_runtime": str(RUNTIME),
            "verification": "aspir_verification_01.json",
            "verification_summary": {
                "total_re_searches": verification.get("total_re_searches"),
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
    print("aspir_freeze_manifest.json written; controller will freeze on next start.")
    return 0


if __name__ == "__main__":
    sys.exit(main())