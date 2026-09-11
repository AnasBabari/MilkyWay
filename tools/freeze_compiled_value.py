"""Freeze a weight-only challenger of an existing compiled candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Refuse to overwrite a frozen candidate")
    old = args.base / "weights/compact_value.npz"
    with np.load(old, allow_pickle=False) as a, np.load(args.weights, allow_pickle=False) as b:
        assert set(a.files) == set(b.files), "Model schema changed"
        for key in a.files:
            assert a[key].shape == b[key].shape, (key, "Model shape changed")
            assert np.isfinite(b[key]).all(), (key, "Nonfinite weights")
    files = list(args.base.glob("*.py")) + [
        p for p in (args.base / "weights").rglob("*") if p.is_file()]
    assert (args.base / "agent.py") in files
    before = {str(p.relative_to(args.base)): sha(p) for p in files}
    args.out.mkdir(parents=True)
    for source in files:
        target = args.out / source.relative_to(args.base)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(args.weights, args.out / "weights/compact_value.npz")
    after = {name: sha(args.out / name) for name in before}
    changed = [name for name in before if before[name] != after[name]]
    assert changed == [str(Path("weights/compact_value.npz"))], changed
    manifest = {"base": str(args.base.resolve()), "base_sha256": before,
                "weights_source": str(args.weights.resolve()), "sha256": after,
                "mechanism": "weights only; source, coefficient and time allocation unchanged",
                "status": "experimental; unpromoted", "changed_files": changed,
                "freezer_sha256": sha(Path(__file__))}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Frozen weight-only challenger: {args.out}")


if __name__ == "__main__":
    main()
