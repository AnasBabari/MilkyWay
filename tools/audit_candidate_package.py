"""Static packaging preflight without building or promoting an archive."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.package import DEFAULT_INCLUDES, members  # noqa: E402
from harness.rules import MAX_UNZIPPED_BYTES  # noqa: E402


def audit(root: Path) -> dict[str, Any]:
    files = list(members(root, DEFAULT_INCLUDES))
    names = [name.replace("\\", "/") for _, name in files]
    assert "agent.py" in names and len(names) == len(set(names))
    manifest = json.loads((root / "manifest.json").read_text())
    expected = {name.replace("\\", "/"): digest for name, digest in manifest["sha256"].items()}
    actual = {name.replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
              for path, name in files}
    assert actual == expected, "Package differs from frozen runtime manifest"
    size = sum(path.stat().st_size for path, _ in files)
    assert size <= MAX_UNZIPPED_BYTES
    local = {Path(name).stem for name in names if name.endswith(".py")}
    allowed = sys.stdlib_module_names | {"chess", "numpy", "numba", "torch", "onnxruntime"}
    imported: set[str] = set()
    for path, name in files:
        assert Path(name).suffix.lower() not in {".exe", ".dll", ".so", ".pyd", ".lib", ".a"}
        if path.suffix != ".py":
            continue
        for node in ast.walk(ast.parse(path.read_bytes())):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg in {"parallel", "cache"}:
                        enabled = isinstance(kw.value, ast.Constant) and kw.value.value is True
                        assert not enabled, (
                            name, "Review cache/parallel runtime setting")
    assert not (imported - allowed - local), imported - allowed - local
    assert not (imported & {"subprocess", "multiprocessing", "socket", "requests", "urllib"})
    return {"candidate": str(root.resolve()), "files": actual, "unzipped_bytes": size,
            "imports": sorted(imported), "matches_frozen_runtime": True,
            "static_preflight_only": True,
            "remaining": ["strength qualification", "exact archive build and extraction",
                          "extracted-archive smoke games", "final artifact checksum"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    reports = [audit(root) for root in args.candidates]
    args.out.write_text(json.dumps(reports, indent=2))
    for report in reports:
        print(json.dumps({"candidate": report["candidate"],
                          "unzipped_bytes": report["unzipped_bytes"],
                          "static_preflight_only": True}))


if __name__ == "__main__":
    main()
