"""Audit existing opening banks and reserve-source provenance without changing banks."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.confirm_bank import CONFIRM_TEST_BANK  # noqa: E402
from tools.screen_bank import SCREEN_TEST_BANK  # noqa: E402
from tools.test_bank import PAIRED_TEST_BANK  # noqa: E402


def fen_key(fen: str) -> str:
    # Conservatively ignore EP and clocks when excluding previously seen boards.
    return " ".join(fen.split()[:3])


def main() -> None:
    root = ROOT / "training/datasets"
    banks = {"screen": SCREEN_TEST_BANK, "confirm": CONFIRM_TEST_BANK,
             "dev": PAIRED_TEST_BANK}
    bank_keys = {name: {fen_key(p.fen) for p in bank} for name, bank in banks.items()}
    used_games: set[str] = set()
    used_positions: set[str] = set()
    evidence = []
    for path in sorted(root.rglob("*.jsonl")):
        relative = path.relative_to(root)
        if "test" in relative.parts or path.name == "test.jsonl":
            continue
        count = 0
        missing_ids = 0
        overlaps = {name: set() for name in banks}
        with path.open(encoding="utf-8") as source:
            for line in source:
                rec = json.loads(line)
                count += 1
                game_id = rec.get("source_game_id")
                if game_id:
                    used_games.add(str(game_id))
                else:
                    missing_ids += 1
                if rec.get("fen"):
                    key = fen_key(rec["fen"])
                    used_positions.add(key)
                    for name in banks:
                        if key in bank_keys[name]:
                            overlaps[name].add(key)
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        evidence.append({"path": str(relative), "sha256": digest, "records": count,
                         "missing_game_ids": missing_ids,
                         "bank_overlap_positions": {k: len(v) for k, v in overlaps.items()}})
    # Existing test records are candidates only if their entire source game is
    # absent from all scanned non-test data. Never infer this from split names.
    candidates = []
    for path in sorted(root.glob("master_value_v*/test.jsonl")):
        eligible_games = set()
        eligible_positions = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            gid = rec.get("source_game_id")
            if not gid or str(gid) in used_games or not rec.get("fen"):
                continue
            key = fen_key(rec["fen"])
            if key in used_positions or any(key in keys for keys in bank_keys.values()):
                continue
            eligible_games.add(str(gid))
            eligible_positions.add(key)
        candidates.append({"path": str(path.relative_to(root)),
                           "unseen_games": len(eligible_games),
                           "unseen_positions": len(eligible_positions)})
    report = {"purpose": "provenance audit, not a claim of complete independence",
              "scope": "all non-test JSONL under training/datasets; excludes NPZ-only data",
              "limitations": ["Missing game IDs and NPZ-only provenance require follow-up",
                              "Previously played tournament games are not audited here",
                              "Shared early openings do not establish shared source games"],
              "non_test_source_games": len(used_games),
              "non_test_positions": len(used_positions), "files": evidence,
              "test_reserve_candidates": candidates}
    out = ROOT / "experiments/compact_cycle_01/promotion_openings_audit.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"non_test_source_games": len(used_games),
                      "non_test_positions": len(used_positions),
                      "test_reserve_candidates": candidates}, indent=2))


if __name__ == "__main__":
    main()
