"""Index previously exposed piece placements for independent-bank screening."""
from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import sys
from pathlib import Path

import chess
import chess.pgn
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from root_policy import board_to_tensor  # noqa: E402


def board_digest(board: chess.Board) -> bytes:
    return hashlib.sha256(np.packbits(board_to_tensor(board)[:12]).tobytes()).digest()


def main(refresh: bool = False) -> None:
    destination = HERE / "confirmation_exclusions_01.sqlite"
    if destination.exists() and not refresh:
        raise RuntimeError("Preserve immutable exclusion index")
    if destination.exists():
        destination.unlink()
    db = sqlite3.connect(destination)
    db.execute("CREATE TABLE positions (digest BLOB PRIMARY KEY) WITHOUT ROWID")
    sources = []
    pending: list[tuple[bytes]] = []

    def flush() -> None:
        db.executemany("INSERT OR IGNORE INTO positions VALUES (?)", pending)
        pending.clear()

    def add_fen(fen: str) -> None:
        pending.append((board_digest(chess.Board(fen)),))
        if len(pending) >= 10000:
            flush()

    inventory = json.loads((HERE / "confirmation_provenance_inventory_01.json").read_text())
    for entry in inventory["npz_inventory"]:
        path = ROOT / entry["path"]
        count = 0
        with np.load(path, allow_pickle=False) as data:
            key = "boards" if "boards" in data.files else "x" if "x" in data.files else None
            if key:
                values = data[key]
                values = values[:, :12].reshape(len(values), 768) if key == "boards" else values
                assert values.shape[1] == 768 and np.all((values == 0) | (values == 1))
                for row in np.packbits(values, axis=1):
                    pending.append((hashlib.sha256(row.tobytes()).digest(),))
                    count += 1
                    if len(pending) >= 10000:
                        flush()
        sources.append({"path": str(path.relative_to(ROOT)), "records": count,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "note": "board placements" if count else
                        "feature-only; tuning_master_value_v2 derives "
                        "from indexed master_value_v2"})
    extra = json.loads((HERE / "search_v2_combined_01_manifest.json")
                       .read_text(encoding="utf-8-sig")) \
        if (HERE / "search_v2_combined_01_manifest.json").exists() else None
    if extra is not None:
        for name, digest in extra["sha256"].items():
            path = ROOT / "experiments/search_v2_combined_01" / name
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
            sources.append({"path": str(path.relative_to(ROOT)),
                            "records": 0,
                            "sha256": digest,
                            "note": "combined candidate source included for "
                            "provenance even though it exposes no positions"})
    for path in sorted((ROOT / "training/datasets").rglob("*.jsonl")):
        count = 0
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                if record.get("fen"):
                    add_fen(record["fen"])
                    count += 1
        sources.append({"path": str(path.relative_to(ROOT)), "records": count,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    print("Tensor and JSONL inputs indexed; checking recorded games and banks", flush=True)
    paths = set((ROOT / "experiments").rglob("manifest.json"))
    paths.update((ROOT / "experiments").glob("**/games/*.json"))
    paths.update((ROOT / "training/datasets").glob("**/game_*.json"))
    paths.add(HERE / "probe_suite_01.json")
    for path in sorted(paths):
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        count = 0
        for row in record.get("positions", []):
            if isinstance(row, dict) and row.get("fen"):
                add_fen(row["fen"])
                count += 1
        if record.get("start_fen"):
            add_fen(record["start_fen"])
            count += 1
        if record.get("pgn"):
            game = chess.pgn.read_game(io.StringIO(record["pgn"]))
            assert game is not None and not game.errors, path
            board = game.board()
            add_fen(board.fen())
            for move in game.mainline_moves():
                assert move in board.legal_moves
                board.push(move)
                add_fen(board.fen())
                count += 1
        if count:
            sources.append({"path": str(path.relative_to(ROOT)), "records": count,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    flush()
    db.commit()
    count = db.execute("SELECT count(*) FROM positions").fetchone()[0]
    db.close()
    report = {"unique_piece_placements": count, "sources": sources,
              "matching": "SHA256 of packed 12 absolute-colour piece planes; "
              "ignores turn/rights/clocks",
              "limitations": "Snapshot. Refresh final tiebreak records before bank acceptance; "
              "also reject colour-reflected bank positions to account for model augmentation.",
              "index_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
    (HERE / "confirmation_exclusions_01.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"unique_piece_placements": count, "sources": len(sources)}), flush=True)


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
