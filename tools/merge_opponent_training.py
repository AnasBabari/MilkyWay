"""Merge opponent trajectories with all occurrences of an opening in one split."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    rows = []
    sources = {}
    agent_hashes = None
    for directory in args.sources:
        assert not (directory / "writer.lock").exists(), "Source still being written"
        manifest = json.loads((directory / "manifest.json").read_text())
        if agent_hashes is None:
            agent_hashes = manifest["source_hashes"]
        assert manifest["source_hashes"] == agent_hashes
        for path in sorted(directory.glob("game_*.json")):
            record = json.loads(path.read_text())
            sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append((path, record, manifest["stockfish"]["level"]))
    openings = sorted({r[1]["start_fen"] for r in rows},
                      key=lambda fen: hashlib.sha256(fen.encode()).hexdigest())
    validation = set(openings[:max(2, round(len(openings) * 0.2))])
    args.out.mkdir(parents=True)
    counts = {"train": 0, "val": 0}
    for index, (path, original, level) in enumerate(rows):
        record = dict(original)
        record["source"] = str(path)
        record["source_game_id"] = original["game_id"]
        record["game_id"] = index
        record["stockfish_level"] = level
        record["split"] = "val" if record["start_fen"] in validation else "train"
        counts[record["split"]] += 1
        (args.out / f"game_{index:05d}.json").write_text(json.dumps(record, indent=2))
    manifest = {"sources": sources, "opening_groups": len(openings),
                "validation_openings": sorted(validation), "games": counts,
                "split_rule": "SHA256-ordered starting-FEN groups; all levels and colours together",
                "purpose": "opponent-training trajectories only, not tournament evidence"}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"openings": len(openings), "games": counts}))


if __name__ == "__main__":
    main()
