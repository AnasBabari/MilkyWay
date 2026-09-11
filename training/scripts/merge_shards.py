"""Merge two labelled shard trees into one training pool.

Copies v2 (master) + v3 (lichess) shards into a combined directory with
global shard numbering per split, plus a merge manifest. No reprocessing.

  .venv/Scripts/python.exe training/scripts/merge_shards.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC_A = Path("training/datasets/master_value_v2")
SRC_B = Path("training/datasets/master_value_v3")
OUT = Path("training/datasets/combined_v2v3")


def main() -> None:
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to mix into non-empty {OUT}")
    manifest: dict[str, object] = {"sources": [str(SRC_A), str(SRC_B)], "splits": {}}
    splits = manifest["splits"]
    assert isinstance(splits, dict)
    total = 0
    for split in ("train", "val", "test"):
        out_dir = OUT / split
        out_dir.mkdir(parents=True, exist_ok=True)
        idx = 0
        files = []
        for src in (SRC_A, SRC_B):
            for path in sorted((src / split).glob("shard_*.npz")):
                dest = out_dir / f"shard_{idx:05d}.npz"
                shutil.copyfile(path, dest)
                files.append(dest.name)
                idx += 1
        import numpy as np

        n = sum(int(np.load(out_dir / f)["boards"].shape[0]) for f in files)
        splits[split] = {"shards": len(files), "positions": n, "files": files}
        total += n
    manifest["total_positions"] = total
    (OUT / "merge_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"merged {total} positions -> {OUT}")


if __name__ == "__main__":
    main()
