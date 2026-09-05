"""Verify versions/mw_0_1 matches commit 772e9a5 (modulo line endings)."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    "agent.py",
    "constants.py",
    "engine.py",
    "engine_types.py",
    "evaluation.py",
    "move_ordering.py",
    "search.py",
    "time_manager.py",
    "transposition.py",
]

ok = True
for name in FILES:
    ref = subprocess.run(
        ["git", "show", f"772e9a5:{name}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8").splitlines()
    snap = (ROOT / "versions" / "mw_0_1" / name).read_text(encoding="utf-8").splitlines()
    if ref == snap:
        print(f"{name}: identical")
    else:
        ok = False
        print(f"{name}: DIFFERS ({len(ref)} vs {len(snap)} lines)")
        import difflib

        for line in list(difflib.unified_diff(ref, snap, lineterm=""))[:20]:
            print("   ", line)
print("SNAPSHOT OK" if ok else "SNAPSHOT MISMATCH")
