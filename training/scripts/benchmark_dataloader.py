# ruff: noqa: E402
"""MilkyWay M17 — Benchmark DataLoader throughput on real shards."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from training.data.dataset import ShardedChessDataset, create_dataloader


def benchmark_dataloader(
    dataset_dir: Path,
    batch_size: int = 512,
    workers_list: list[int] | None = None,
) -> None:
    if workers_list is None:
        workers_list = [0, 2, 4]
    train_shards = sorted(list((dataset_dir / "train").glob("*.npz")))
    dataset = ShardedChessDataset(train_shards)
    print(f"Dataset total samples: {len(dataset):,} across {len(train_shards)} shards")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Target device: {device}\n")
    header = (
        f"{'Workers':<8} | {'Batch Size':<10} | "
        f"{'Throughput (samples/s)':<22} | {'Time (s)':<10}"
    )
    print(header)
    print("-" * 55)

    for w in workers_list:
        loader = create_dataloader(
            dataset, batch_size=batch_size, shuffle=True, num_workers=w, pin_memory=True
        )
        # Iterate 1 full pass
        t0 = time.perf_counter()
        count = 0
        for batch in loader:
            boards = batch["board"].to(device, non_blocking=True)
            count += boards.shape[0]

        elapsed = time.perf_counter() - t0
        sps = count / elapsed
        print(f"{w:<8} | {batch_size:<10} | {sps:<22.1f} | {elapsed:<10.2f}")


if __name__ == "__main__":
    benchmark_dataloader(ROOT / "training" / "datasets" / "smoke_50k")
