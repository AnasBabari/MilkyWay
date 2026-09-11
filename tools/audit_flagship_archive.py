"""Compare the frozen opponent's runtime bytes with saved submission archives."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    baseline = root / "experiments/silky_snow"
    paths = [*sorted(baseline.glob("*.py")), baseline / "weights/milkyway_policy.onnx"]
    expected = {p.relative_to(baseline).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in paths}
    reports = []
    for path in (baseline / "agent.zip", root / "agent_silky_snow.zip", root / "agent.zip"):
        if not path.exists():
            reports.append({"archive": str(path), "exists": False})
            continue
        with zipfile.ZipFile(path) as archive:
            actual = {name: hashlib.sha256(archive.read(name)).hexdigest()
                      for name in archive.namelist() if not name.endswith("/")}
        reports.append({"archive": str(path), "exists": True,
                        "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "missing": sorted(set(expected) - set(actual)),
                        "different": [n for n in expected
                                      if n in actual and expected[n] != actual[n]],
                        "extra": sorted(set(actual) - set(expected))})
    out = root / "experiments/compact_cycle_01/flagship_archive_audit.json"
    out.write_text(json.dumps({"runtime_hashes": expected, "archives": reports}, indent=2))
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
