"""Prepare isolated single-mechanism candidate snapshots for R34 testing."""

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


def prepare_lmr_candidate() -> None:
    dest = R34 / "lmr_candidate"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for rel in RUNTIME_FILES:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CHECKPOINT / rel, target)

    search_file = dest / "search.py"
    content = search_file.read_text(encoding="utf-8")

    # Replace in _negamax:
    target_text = (
        "            board.push(move)\n"
        "            self._stack_keys.append(board._transposition_key())\n"
        "            try:\n"
        "                if index == 0:\n"
        "                    score = -self._negamax("
        "board, depth - 1, -beta, -alpha, ply + 1, True, {})\n"
        "                else:\n"
        "                    # LMR: late quiet moves get reduced depth first.\n"
        "                    reduced = depth - 1\n"
        "                    do_lmr = (\n"
        "                        not self._emergency\n"
        "                        and depth >= LMR_MIN_DEPTH\n"
        "                        and index >= LMR_MOVE_INDEX\n"
        "                        and not tactical\n"
        "                        and not in_check\n"
        "                    )\n"
    )

    replacement_text = (
        "            gives_check = board.gives_check(move)\n"
        "            board.push(move)\n"
        "            self._stack_keys.append(board._transposition_key())\n"
        "            try:\n"
        "                if index == 0:\n"
        "                    score = -self._negamax("
        "board, depth - 1, -beta, -alpha, ply + 1, True, {})\n"
        "                else:\n"
        "                    # LMR: late quiet moves get reduced depth first.\n"
        "                    reduced = depth - 1\n"
        "                    do_lmr = (\n"
        "                        not self._emergency\n"
        "                        and depth >= LMR_MIN_DEPTH\n"
        "                        and index >= LMR_MOVE_INDEX\n"
        "                        and not tactical\n"
        "                        and not in_check\n"
        "                        and not gives_check\n"
        "                    )\n"
    )

    assert target_text in content, "Failed to match target text in search.py for LMR candidate"
    search_file.write_text(content.replace(target_text, replacement_text), encoding="utf-8")
    print("[OK] Created lmr_candidate with search.py LMR check exclusion")


def prepare_ksq_candidate() -> None:
    dest = R34 / "ksq_candidate"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for rel in RUNTIME_FILES:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CHECKPOINT / rel, target)

    eval_file = dest / "evaluation.py"
    content = eval_file.read_text(encoding="utf-8")

    target_text = (
        "    mg += wks - bks\n"
        "    eg += int((wks - bks) * 0.2)\n"
    )

    replacement_text = (
        "    wks_eg_scale = 1.0 if b_queens_mask else 0.2\n"
        "    bks_eg_scale = 1.0 if w_queens_mask else 0.2\n"
        "    mg += wks - bks\n"
        "    eg += int(wks * wks_eg_scale - bks * bks_eg_scale)\n"
    )

    assert target_text in content, "Failed to match target text in evaluation.py for KSQ candidate"
    eval_file.write_text(content.replace(target_text, replacement_text), encoding="utf-8")
    print("[OK] Created ksq_candidate with queen-aware king safety scaling")


def verify_diffs() -> None:
    print("=== Verifying diffs against frozen checkpoint ===")
    for cand_name, mod_file in (("lmr_candidate", "search.py"), ("ksq_candidate", "evaluation.py")):
        cand_dir = R34 / cand_name
        for rel in RUNTIME_FILES:
            cp_bytes = (CHECKPOINT / rel).read_bytes()
            cand_bytes = (cand_dir / rel).read_bytes()
            if rel == mod_file:
                assert cp_bytes != cand_bytes, f"Expected {rel} to differ in {cand_name}!"
                diff = list(
                    difflib.unified_diff(
                        cp_bytes.decode("utf-8").splitlines(),
                        cand_bytes.decode("utf-8").splitlines(),
                        fromfile=f"checkpoint/{rel}",
                        tofile=f"{cand_name}/{rel}",
                    )
                )
                print(f"[PASS] {cand_name}/{rel} diff verified ({len(diff)} lines)")
            else:
                assert cp_bytes == cand_bytes, f"Unexpected difference in {cand_name}/{rel}!"
        print(f"[PASS] {cand_name} has exactly 1 modified file: {mod_file}")


def update_snapshots_json() -> None:
    snapshots_file = R34 / "snapshots.json"
    data = json.loads(snapshots_file.read_text(encoding="utf-8")) if snapshots_file.exists() else {}
    data["checkpoint"] = hash_dir(CHECKPOINT)
    data["lmr_candidate"] = hash_dir(R34 / "lmr_candidate")
    data["ksq_candidate"] = hash_dir(R34 / "ksq_candidate")
    snapshots_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("[OK] Updated snapshots.json")


def main() -> None:
    prepare_lmr_candidate()
    prepare_ksq_candidate()
    verify_diffs()
    update_snapshots_json()


if __name__ == "__main__":
    main()
