"""Merge any number of shard trees into one training pool.

  training/.venv/Scripts/python.exe training/scripts/merge_shards_generic.py \
      --out training/datasets/pretrain_v5 \
      --src training/datasets/combined_v2v3 training/datasets/master_value_v4
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--src", type=Path, nargs="+", required=True)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit(f"refusing to mix into non-empty {args.out}")
    manifest: dict[str, object] = {"sources": [str(s) for s in args.src], "splits": {}}
    splits = manifest["splits"]
    assert isinstance(splits, dict)
    total = 0
    for split in ("train", "val", "test"):
        out_dir = args.out / split
        out_dir.mkdir(parents=True, exist_ok=True)
        idx = 0
        files: list[str] = []
        for src in args.src:
            for path in sorted((src / split).glob("shard_*.npz")):
                dest = out_dir / f"shard_{idx:05d}.npz"
                shutil.copyfile(path, dest)
                files.append(dest.name)
                idx += 1
        n = sum(int(np.load(out_dir / f, mmap_mode="r")["boards"].shape[0]) for f in files)
        splits[split] = {"shards": len(files), "positions": n, "files": files}
        total += n
    manifest["total_positions"] = total
    (args.out / "merge_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"merged {total} positions -> {args.out}")


if __name__ == "__main__":
    main()