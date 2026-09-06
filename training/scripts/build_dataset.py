# ruff: noqa: E402
"""MilkyWay M17 — Build sharded training dataset.

Usage:
  python training/scripts/build_dataset.py --target-positions 50000
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.data.collector import build_smoke_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Build sharded chess dataset.")
    parser.add_argument(
        "--target-positions", type=int, default=50000, help="Total positions to collect"
    )
    parser.add_argument("--shard-size", type=int, default=10000, help="Positions per shard")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "training" / "datasets" / "smoke_50k",
        help="Output dataset directory",
    )
    parser.add_argument(
        "--pgn-dir",
        type=Path,
        default=ROOT / "training" / "data" / "raw_pgn",
        help="Directory containing downloaded PGNs",
    )
    args = parser.parse_args()

    print(f"Building dataset with target {args.target_positions:,} positions...")
    t0 = time.perf_counter()
    shards = build_smoke_dataset(
        output_base_dir=args.output_dir,
        target_positions=args.target_positions,
        shard_size=args.shard_size,
        pgn_path=args.pgn_dir,
    )
    elapsed = time.perf_counter() - t0

    print(f"\nDataset build finished in {elapsed:.1f}s:")
    for split_name, s_list in shards.items():
        total_bytes = sum(p.stat().st_size for p in s_list)
        mb = total_bytes / (1024 * 1024)
        print(f"  Split '{split_name}': {len(s_list)} shards ({mb:.2f} MB)")


if __name__ == "__main__":
    main()
