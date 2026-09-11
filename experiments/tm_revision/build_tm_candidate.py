"""Build the TM-ceiling variant (deterministic, reviewable).

Copies experiments/search_v2_nmp_01 -> experiments/search_v2_tm_01, then ONLY
raises the healthy-clock single-move caps in time_manager.py:
  TM_SOFT_CAP_MS 3500 -> 6000, hard cap 6500 -> 12000 (time_left > 90s branch).
Rationale (rated-clock evidence): slowest move pegs the 6.5s hard cap in EVERY
rated game while 20-100s remain; habitual spending (~3s) is set by the divisor,
not the caps, so only the starved critical moves change. Emergency, low-clock,
margin, and single-move paths are byte-identical. Env overrides retained.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "experiments/search_v2_nmp_01"
DST = ROOT / "experiments/search_v2_tm_01"


def main() -> None:
    if DST.exists():
        raise SystemExit(f"Refusing to overwrite {DST}")
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
    path = DST / "time_manager.py"
    text = path.read_text()

    old_soft = 'TM_SOFT_CAP_MS: float = _env_float("MILKYWAY_TM_SOFT_CAP_MS", 3500.0)'
    assert text.count(old_soft) == 1
    text = text.replace(
        old_soft,
        'TM_SOFT_CAP_MS: float = _env_float("MILKYWAY_TM_SOFT_CAP_MS", 6000.0)',
    )
    old_hard = """        if time_left > 90000.0:
            soft = min(soft, TM_SOFT_CAP_MS)
            hard = min(hard, 6500.0)"""
    assert text.count(old_hard) == 1
    text = text.replace(
        old_hard,
        """        if time_left > 90000.0:
            soft = min(soft, TM_SOFT_CAP_MS)
            hard = min(hard, 12000.0)""",
    )
    path.write_text(text)

    src_manifest = json.loads((SRC / "manifest.json").read_text())
    frozen = dict(src_manifest.get("sha256", {}))
    frozen["time_manager.py"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"candidate": "search_v2_tm_01", "base": "search_v2_nmp_01",
                "change": "healthy-clock caps 3.5s->6s soft, 6.5s->12s hard (see TM_DESIGN.md)",
                "sha256": frozen}
    (DST / "manifest.json").write_text(json.dumps(manifest, indent=1))

    ruff = subprocess.run([sys.executable, "-m", "ruff", "check", str(path)],
                          capture_output=True, text=True)
    print(ruff.stdout.strip() or ruff.stderr.strip())
    if ruff.returncode != 0:
        raise SystemExit("ruff failed on the patched file")
    print(f"built {DST}")


if __name__ == "__main__":
    main()
