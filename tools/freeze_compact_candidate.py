"""Freeze a compact candidate with explicit model and residual coefficient."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--coefficient", type=float, default=1.0)
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Use a new immutable candidate directory")
    assert 0 <= args.coefficient <= 1
    (args.out / "weights").mkdir(parents=True)
    for path in args.base.glob("*.py"):
        shutil.copy2(path, args.out / path.name)
    shutil.copy2(args.policy or args.base / "weights/milkyway_policy.onnx",
                 args.out / "weights/milkyway_policy.onnx")
    shutil.copy2(args.weights, args.out / "weights/compact_value.npz")
    wrapper = args.out / "compact_value.py"
    text = wrapper.read_text()
    lines = [line.strip() for line in text.splitlines()
             if line.strip().startswith("correction = round(")]
    assert len(lines) == 1 and "residual_white(board)" in lines[0]
    old = lines[0]
    wrapper.write_text(text.replace(old,
        f"correction = round({args.coefficient!r} * residual_white(board))"))
    paths = list(args.out.glob("*.py")) + list((args.out / "weights").glob("*"))
    manifest = {"base": str(args.base.resolve()), "weights_source": str(args.weights.resolve()),
                "coefficient": args.coefficient, "status": "unpromoted experimental candidate",
                "sha256": {str(p.relative_to(args.out)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in paths}}
    (args.out / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
