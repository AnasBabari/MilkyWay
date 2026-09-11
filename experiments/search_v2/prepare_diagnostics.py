"""Create an isolated diagnostic copy from our existing, frozen ordered search."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> None:
    base = ROOT / "experiments/compiled_ordered_01"
    manifest = json.loads((base / "manifest.json").read_text())
    out = HERE / "diagnostic_runtime_01"
    out.mkdir(exist_ok=False)
    for name, digest in manifest["sha256"].items():
        data = (base / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    source = ROOT / "experiments/compiled_core_01/reduced_search.py"
    text = source.read_text()
    replacements = [
        ("    if tick(stats, deadline):\n", "    stats[5] += int(depth <= 0)\n"
         "    stats[6] = max(stats[6], ply)\n"
         "    stats[7] = max(stats[7], -depth)\n"
         "    if tick(stats, deadline):\n"),
        ("    count = len(moves)\n    check =", "    count = len(moves)\n"
         "    stats[8] += count\n    check ="),
        ("    if ply >= LIMIT:\n", "    if ply >= LIMIT:\n        stats[9] += 1\n"),
        ("    if depth > 0 and tt_data[slot, 1]", "    if depth > 0:\n"
         "        stats[10] += 1\n    if depth > 0 and tt_data[slot, 1]"),
        ("        preferred = tt_data[slot, 3]\n", "        stats[11] += 1\n"
         "        preferred = tt_data[slot, 3]\n"),
        ("            value = unpack_mate", "            stats[12] += 1\n"
         "            value = unpack_mate"),
        ("        undo = make_move(board, move, rights, ep)\n",
         "        stats[13] += 1\n        undo = make_move(board, move, rights, ep)\n"),
        ("        else:\n            reduced_depth =", "        else:\n"
         "            stats[14] += 1\n            reduced_depth ="),
        ("            if not stats[1] and alpha < -value < beta:\n",
         "            if not stats[1] and alpha < -value < beta:\n"
         "                stats[15] += 1\n"),
        ("        if alpha >= beta:\n", "        if alpha >= beta:\n"
         "            stats[16] += 1\n            stats[17] += int(i == 0)\n"),
        ("stats = np.zeros(5, dtype=np.int64)", "stats = np.zeros(18, dtype=np.int64)"),
        ('"reduction_researches": int(stats[4])}',
         '"reduction_researches": int(stats[4]),\n'
         '            "metrics": {"qnodes": int(stats[5]), "max_ply": int(stats[6]),\n'
         '                "max_qdepth": int(stats[7]), "generated_moves": int(stats[8]),\n'
         '                "ply_cap_hits": int(stats[9]), "tt_probes": int(stats[10]),\n'
         '                "tt_position_hits": int(stats[11]),\n'
         '                "tt_context_depth_hits": int(stats[12]),\n'
         '                "tt_cutoffs": int(stats[2]), "searched_moves": int(stats[13]),\n'
         '                "pvs_scouts": int(stats[14]), "pvs_researches": int(stats[15]),\n'
         '                "beta_cutoffs": int(stats[16]),\n'
         '                "first_move_beta_cutoffs": int(stats[17])}}'),
    ]
    for before, after in replacements:
        assert text.count(before) == 1, before
        text = text.replace(before, after)
    (out / "diagnostic_search.py").write_text(text)
    record = {"purpose": "diagnostic only; not selected production baseline",
              "parent": str(base), "parent_sha256": manifest["sha256"],
              "own_lmr_source": str(source),
              "own_lmr_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "diagnostic_sha256": hashlib.sha256(text.encode()).hexdigest(),
              "mechanisms": "LMR toggle and counters; frozen evaluation/time unchanged"}
    (out / "diagnostic_manifest.json").write_text(json.dumps(record, indent=2))
    print(out)


if __name__ == "__main__":
    main()
