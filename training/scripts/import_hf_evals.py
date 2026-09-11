"""Import high-quality Stockfish-evaluated positions from HuggingFace.

Downloads Lichess/chess-position-evaluations parquet files locally,
streams them in chunks, filters for quality, and exports to NPZ shards.

  training/.venv/Scripts/python.exe training/scripts/import_hf_evals.py \
      --out training/datasets/lichess_eval_v1 --target-positions 500000
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.data.representation import board_to_tensor  # noqa: E402

import chess  # noqa: E402

HF_REPO = "Lichess/chess-position-evaluations"
HF_SUBDIR = "data"


def download_parquet(file_idx: int, cache_dir: Path) -> Path | None:
    """Download a single parquet file from HF Hub."""
    filename = f"{HF_SUBDIR}/data_{file_idx:04d}.parquet"
    local_path = cache_dir / f"data_{file_idx:04d}.parquet"
    if local_path.exists() and local_path.stat().st_size > 1_000_000_000:
        print(f"Using cached {local_path.name}")
        return local_path

    try:
        from huggingface_hub import hf_hub_download

        print(f"Downloading {filename} ...")
        downloaded = hf_hub_download(
            repo_id=HF_REPO,
            filename=filename,
            repo_type="dataset",
            local_dir=str(cache_dir),
            local_dir_use_symlinks=False,
        )
        return Path(downloaded)
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return None


def stream_parquet_local(path: Path, batch_size: int = 65536):
    """Yield record batches from a local parquet file."""
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=batch_size):
        yield batch


def process_batch(batch, collected_fens, collected_values, target_count):
    """Filter a pyarrow batch and append valid (fen, cp) pairs."""
    fens = batch.column("fen").to_pylist()
    cps = batch.column("cp").to_pylist()
    mates = batch.column("mate").to_pylist()
    depths = batch.column("depth").to_pylist()
    knodes = batch.column("knodes").to_pylist()

    need = target_count - len(collected_fens)
    if need <= 0:
        return

    valid_fens = []
    valid_values = []
    for fen, cp, mate, depth, kn in zip(fens, cps, mates, depths, knodes):
        if mate is not None:
            continue
        if depth < 20:
            continue
        if kn < 100_000:
            continue
        if cp is None:
            continue
        cp_val = int(cp)
        if abs(cp_val) > 1000:
            continue
        valid_fens.append(fen)
        valid_values.append(cp_val)
        if len(valid_fens) >= need:
            break

    collected_fens.extend(valid_fens)
    collected_values.extend(valid_values)


def encode_and_save(fens, values, out_dir: Path, shard_idx: int):
    """Convert FENs to tensors and save as NPZ."""
    tensors = []
    valid_values = []
    for fen, cp in zip(fens, values):
        try:
            board = chess.Board(fen)
            if board.is_check():
                continue
            tensor = board_to_tensor(board)
            tensors.append(tensor)
            valid_values.append(cp)
        except Exception:
            continue

    if not tensors:
        return False

    X = np.stack(tensors, axis=0).astype(np.uint8)
    y = np.array(valid_values, dtype=np.float32)
    out_path = out_dir / f"shard_{shard_idx:04d}.npz"
    np.savez_compressed(out_path, X=X, y=y)
    print(f"Saved {out_path}: {len(y)} positions")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--target-positions", type=int, default=500_000)
    parser.add_argument("--shard-size", type=int, default=50_000)
    parser.add_argument("--max-files", type=int, default=3)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "training" / "data" / "hf_raw")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    collected_fens: list[str] = []
    collected_values: list[int] = []
    shard_idx = 0
    total_saved = 0

    pbar = tqdm(total=args.target_positions, desc="Collecting positions")

    for file_idx in range(args.max_files):
        if len(collected_fens) >= args.target_positions:
            break

        local_path = download_parquet(file_idx, args.cache_dir)
        if local_path is None:
            continue

        print(f"Processing {local_path.name} ...")
        try:
            for batch in stream_parquet_local(local_path):
                process_batch(batch, collected_fens, collected_values, args.target_positions)
                pbar.update(len(collected_fens) - pbar.n)
                while len(collected_fens) >= args.shard_size:
                    fens = collected_fens[: args.shard_size]
                    values = collected_values[: args.shard_size]
                    collected_fens = collected_fens[args.shard_size :]
                    collected_values = collected_values[args.shard_size :]
                    if encode_and_save(fens, values, args.out, shard_idx):
                        shard_idx += 1
                        total_saved += len(fens)
                if len(collected_fens) >= args.target_positions:
                    break
        except Exception as e:
            print(f"Error processing file {file_idx}: {e}")
            continue
        finally:
            # Clean up downloaded file to save disk space
            if local_path.exists():
                local_path.unlink()
                print(f"Cleaned up {local_path.name}")

    pbar.close()

    # Flush remainder
    if collected_fens:
        encode_and_save(collected_fens, collected_values, args.out, shard_idx)
        total_saved += len(collected_fens)

    print(f"\nDone. Saved ~{total_saved} positions to {args.out}")


if __name__ == "__main__":
    main()
