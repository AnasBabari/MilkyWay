# ruff: noqa: E402
"""Label value-dataset records with full-strength Stockfish (multi-worker).

Reads train/val/test.jsonl from a records directory, evaluates every
position with Stockfish at a fixed node budget, and writes sharded NPZ files
via the canonical schema (boards, policy, WDL, value, soft targets).

  training/.venv/Scripts/python.exe training/scripts/label_value_dataset.py \
      --records training/datasets/master_value_v1 --nodes 50000 --workers 8
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import chess.engine

from training.data.dataset import PositionRecord, write_shard_npz
from training.scripts.label_stockfish import label_position

CANDIDATE_BINARIES = (
    Path("C:/Users/Babar/AppData/Local/Temp/opencode/sf/stockfish/stockfish-windows-x86-64-universal.exe"),
    Path("C:/Users/Babar/AppData/Local/Microsoft/WinGet/Packages/Stockfish.Stockfish_Microsoft.Winget.Source_8wekyb3d8bbwe/stockfish/stockfish-windows-x86-64-avx2.exe"),
)


def resolve_binary(explicit: str | None) -> Path:
    import os

    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    env = os.environ.get("STOCKFISH_PATH")
    if env and Path(env).is_file():
        return Path(env)
    for p in CANDIDATE_BINARIES:
        if p.is_file():
            return p
    raise SystemExit("no Stockfish binary found; pass --stockfish or set STOCKFISH_PATH")


def label_chunk(
    binary: str, nodes: int, multipv: int, records: list[dict[str, object]]
) -> list[dict[str, object]]:
    """Label one chunk in a worker process. Returns updated record dicts."""
    out: list[dict[str, object]] = []
    with chess.engine.SimpleEngine.popen_uci(binary) as engine:
        engine.configure({"Threads": 1, "Hash": 64})
        for rec in records:
            fen = rec["fen"]
            assert isinstance(fen, str)
            try:
                label = label_position(engine, fen, nodes=nodes, multipv=multipv)
            except Exception:
                continue
            rec["stockfish_cp"] = label.cp
            rec["stockfish_wdl"] = label.wdl
            rec["stockfish_top_k"] = label.top_k_moves
            rec["stockfish_scores"] = label.top_k_scores
            out.append(rec)
    return out


def split_chunks(items: list[dict[str, object]], n: int) -> list[list[dict[str, object]]]:
    return [items[i::n] for i in range(n)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--stockfish", type=str, default=None)
    parser.add_argument("--nodes", type=int, default=50000)
    parser.add_argument("--multipv", type=int, default=4)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--shard-size", type=int, default=8000)
    parser.add_argument("--limit", type=int, default=0, help="pilot cap per split (0 = all)")
    args = parser.parse_args()

    binary = resolve_binary(args.stockfish)
    print(f"binary: {binary}")

    for split in ("train", "val", "test"):
        src = args.records / f"{split}.jsonl"
        if not src.is_file():
            print(f"skip missing {src}")
            continue
        records = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
        if args.limit:
            records = records[: args.limit]
        print(f"{split}: labelling {len(records)} positions ...", flush=True)
        chunks = split_chunks(records, max(1, args.workers))
        labelled: list[PositionRecord] = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(label_chunk, str(binary), args.nodes, args.multipv, chunk)
                for chunk in chunks
                if chunk
            ]
            for done, fut in enumerate(futures, start=1):
                for rec in fut.result():
                    labelled.append(PositionRecord.from_dict(rec))
                print(f"  workers done {done}/{len(futures)}", flush=True)
        out_dir = args.records / split
        out_dir.mkdir(exist_ok=True)
        shard_paths: list[str] = []
        for i in range(0, len(labelled), args.shard_size):
            path = out_dir / f"shard_{i // args.shard_size:05d}.npz"
            write_shard_npz(labelled[i : i + args.shard_size], path)
            shard_paths.append(path.name)
        manifest = {
            "split": split,
            "labelled": len(labelled),
            "nodes": args.nodes,
            "multipv": args.multipv,
            "binary": str(binary),
            "shards": shard_paths,
            "shard_sha256": {
                name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
                for name in shard_paths
            },
        }
        (out_dir / "label_manifest.json").write_text(json.dumps(manifest, indent=1))
        print(f"{split}: {len(labelled)} labelled -> {len(shard_paths)} shards")


if __name__ == "__main__":
    main()
