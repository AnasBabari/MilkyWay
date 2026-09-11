"""Prepare and verify speed_candidate for R34 tournament screening."""

from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

R34 = ROOT / "experiments" / "r34"
CHECKPOINT = R34 / "checkpoint"

RUNTIME_FILES = (
    "agent.py",
    "constants.py",
    "engine.py",
    "engine_types.py",
    "evaluation.py",
    "move_ordering.py",
    "root_policy.py",
    "search.py",
    "time_manager.py",
    "transposition.py",
    "weights/milkyway_policy.onnx",
)


def hash_dir(directory: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel in RUNTIME_FILES:
        path = directory / rel
        hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def prepare_speed_candidate() -> None:
    dest = R34 / "speed_candidate"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for rel in RUNTIME_FILES:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CHECKPOINT / rel, target)

    # 1. Update evaluation.py: set default to MW_0_2_KS_C
    eval_file = dest / "evaluation.py"
    eval_content = eval_file.read_text(encoding="utf-8")
    assert eval_content.count("else MW_0_2_EVAL\n") == 1
    new_eval = eval_content.replace("else MW_0_2_EVAL\n", "else MW_0_2_KS_C\n")
    eval_file.write_text(new_eval, encoding="utf-8")
    print("[OK] Updated evaluation.py with MW_0_2_KS_C default")

    # 2. Update search.py: quiescence legal captures + integer tie-break
    search_file = dest / "search.py"
    search_content = search_file.read_text(encoding="utf-8")

    old_cap = "m for m in board.legal_moves if board.is_capture(m) or m.promotion is not None"
    target_text = (
        f"        captures: list[chess.Move] = [\n            {old_cap}\n        ]\n"
        "        if not captures:\n"
        "            return alpha\n"
        "        # Order captures by MVV-LVA (deterministic).\n"
        "        captures.sort(key=lambda m: (-capture_mvv_lva(board, m), m.uci()))\n"
    )

    replacement_text = (
        "        pawns = board.pawns & board.occupied_co[board.turn]\n"
        "        seventh_rank = chess.BB_RANK_7 if board.turn == chess.WHITE else chess.BB_RANK_2\n"
        "        if pawns & seventh_rank:\n"
        f"            captures: list[chess.Move] = [\n                {old_cap}\n            ]\n"
        "        else:\n"
        "            captures = list(board.generate_legal_captures())\n"
        "        if not captures:\n"
        "            return alpha\n"
        "        # Order captures by MVV-LVA (deterministic).\n"
        "        captures.sort(\n"
        "            key=lambda m: (\n"
        "                -capture_mvv_lva(board, m),\n"
        "                (m.from_square << 6) | m.to_square | ((m.promotion or 0) << 12),\n"
        "            )\n"
        "        )\n"
    )

    assert target_text in search_content, "Target text not found in search.py!"
    search_file.write_text(search_content.replace(target_text, replacement_text), encoding="utf-8")
    print("[OK] Updated search.py with generate_legal_captures and integer tie-break")


def verify_diffs() -> None:
    print("=== Verifying diffs against frozen checkpoint ===")
    cand_dir = R34 / "speed_candidate"
    modified_files = set()
    for rel in RUNTIME_FILES:
        cp_bytes = (CHECKPOINT / rel).read_bytes()
        cand_bytes = (cand_dir / rel).read_bytes()
        if cp_bytes != cand_bytes:
            modified_files.add(rel)
            diff = list(
                difflib.unified_diff(
                    cp_bytes.decode("utf-8").splitlines(),
                    cand_bytes.decode("utf-8").splitlines(),
                    fromfile=f"checkpoint/{rel}",
                    tofile=f"speed_candidate/{rel}",
                )
            )
            print(f"[PASS] speed_candidate/{rel} diff verified ({len(diff)} lines)")
        else:
            print(f"[PASS] speed_candidate/{rel} identical to checkpoint")

    expected_mod = {"evaluation.py", "search.py"}
    assert modified_files == expected_mod, f"Unexpected modified files: {modified_files}"
    print(f"[PASS] Exactly modified files: {modified_files}")


def update_snapshots_json() -> None:
    snapshots_file = R34 / "snapshots.json"
    data = json.loads(snapshots_file.read_text(encoding="utf-8")) if snapshots_file.exists() else {}
    data["speed_candidate"] = hash_dir(R34 / "speed_candidate")
    snapshots_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("[OK] Updated snapshots.json with speed_candidate hashes")


def main() -> None:
    prepare_speed_candidate()
    verify_diffs()
    update_snapshots_json()


if __name__ == "__main__":
    main()
