"""Encode train/val/test.jsonl record sets into canonical NPZ shards.

Skips Stockfish labelling entirely (value/soft targets stay masked); used to
pretrain policy + trunk at scale before any value fine-tune. Mirrors the
shard layout produced by label_value_dataset.py so both can be merged.

  training/.venv/Scripts/python.exe training/scripts/encode_splits.py \\
      --records training/datasets/master_value_v4 --shard-size 8000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.data.dataset import PositionRecord, write_shard_npz  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--shard-size", type=int, default=8000)
    args = parser.parse_args()

    for split in ("train", "val", "test"):
        src = args.records / f"{split}.jsonl"
        if not src.is_file():
            print(f"skip missing {src}")
            continue
        with src.open(encoding="utf-8") as fh:
            records = [PositionRecord.from_dict(json.loads(line)) for line in fh if line.strip()]
        if not records:
            print(f"{split}: empty")
            continue
        out_dir = args.records / split
        out_dir.mkdir(exist_ok=True)
        shard_paths: list[str] = []
        for i in range(0, len(records), args.shard_size):
            path = out_dir / f"shard_{i // args.shard_size:05d}.npz"
            write_shard_npz(records[i : i + args.shard_size], path)
            shard_paths.append(path.name)
        manifest = {
            "split": split,
            "encoded": len(records),
            "shards": shard_paths,
            "shard_sha256": {
                name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
                for name in shard_paths
            },
        }
        (out_dir / "label_manifest.json").write_text(json.dumps(manifest, indent=1))
        print(f"{split}: {len(records)} encoded -> {len(shard_paths)} shards")


if __name__ == "__main__":
    main()