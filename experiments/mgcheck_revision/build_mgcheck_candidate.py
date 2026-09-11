"""Build the isolated check-extension candidate (deterministic, reviewable).

Copies experiments/search_v2_nmp_mg_01 -> experiments/search_v2_mg_checkext_01,
then ONLY extends checking moves by one ply at depth>=1 nodes:
  child_base = depth - 1 + (1 if move gives check else 0)
Checking moves are already LMR-exempt; the extension composes with it.
No history/TT/eval/clock change. Ply LIMIT caps runaway lines.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "experiments/search_v2_nmp_mg_01"
DST = ROOT / "experiments/search_v2_mg_checkext_01"

EXT_BLOCK = '''        undo = make_move(board, move, rights, ep)
        child_halfmove = 0 if pawn or capture else halfmove + 1
        gives_check = attacked(board, king_square(board, -side), side)
        ext = 1 if (depth >= 1 and ext_used < 3 and gives_check) else 0
        child_base = depth - 1 + ext
        if ext:
            stats[6] += 1
'''
MAX_EXT_NOTE = "max 3 check extensions per path (bounds checking-line explosion)"


def main() -> None:
    if DST.exists():
        raise SystemExit(f"Refusing to overwrite {DST}")
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
    path = DST / "combined_search.py"
    text = path.read_text()

    old_make = ("        undo = make_move(board, move, rights, ep)\n"
                "        child_halfmove = 0 if pawn or capture else halfmove + 1\n")
    assert text.count(old_make) == 1
    text = text.replace(old_make, EXT_BLOCK, 1)

    # all child searches use the extended base depth
    old_depth = "depth - 1, -beta, -alpha, ply + 1,"
    assert text.count(old_depth) == 2  # full-window + PVS research paths
    text = text.replace(old_depth, "child_base, -beta, -alpha, ply + 1,")
    old_null = "depth - 1, -alpha - 1, -alpha, ply + 1,"
    assert text.count(old_null) == 1  # LMR research path only (null-window uses reduced_depth)
    text = text.replace(old_null, "child_base, -alpha - 1, -alpha, ply + 1,")
    old_red = "reduced_depth = depth - 1"
    assert text.count(old_red) == 1
    text = text.replace(old_red, "reduced_depth = child_base")
    text = text.replace(
        "reduced_depth = max(1, depth - (3 if depth >= 6 and i >= 10 else 2))",
        "reduced_depth = max(1, child_base - (3 if depth >= 6 and i >= 10 else 2))")

    # thread the per-path extension budget (indents measured programmatically:
    # recursions at 31sp (x2) and 32sp (x2), root at 30sp/31sp, null call aside)
    old_root = ("len(prior_keys) + 1, stats, deadline, coefficient, best,\n"
                "                              tt_keys, tt_context, "
                "tt_data, killers, move_history, lmr_enabled,\n"
                "                               True)")
    assert text.count(old_root) == 1
    text = text.replace(
        old_root,
        "len(prior_keys) + 1, stats, deadline, coefficient, best,\n"
        "                              tt_keys, tt_context, "
        "tt_data, killers, move_history, lmr_enabled,\n"
        "                               True, 0)")
    old31 = "move_history, lmr_enabled,\n                               True)"
    assert text.count(old31) == 2
    text = text.replace(
        old31,
        "move_history, lmr_enabled,\n                               True, ext_used + ext)")
    old32 = "move_history, lmr_enabled,\n                                True)"
    assert text.count(old32) == 2
    text = text.replace(
        old32,
        "move_history, lmr_enabled,\n                                True, ext_used + ext)")
    old_nmp = "lmr_enabled, False)"
    assert text.count(old_nmp) == 1  # NMP null search keeps the incoming budget
    text = text.replace(old_nmp, "lmr_enabled, False, ext_used)")
    # signature gains the per-path budget counter
    old_sig = ("tt_keys, tt_context, tt_data, killers, move_history,"
               " lmr_enabled,\n            null_ok):")
    assert text.count(old_sig) == 1
    text = text.replace(
        old_sig,
        "tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,\n"
        "            null_ok, ext_used):")

    assert "stats = np.zeros(6, dtype=np.int64)" in text
    text = text.replace("stats = np.zeros(6, dtype=np.int64)",
                        "stats = np.zeros(7, dtype=np.int64)")
    old_rep = '"null_cutoffs": int(stats[5])}'
    assert old_rep in text
    text = text.replace(
        old_rep,
        '"null_cutoffs": int(stats[5]),\n'
        '             "check_extensions": int(stats[6])}')

    text = text.replace(
        "Null-move pruning\n(R=2/3, conservative zugzwang guards) is added;",
        "Null-move pruning\n(R=2/3, conservative zugzwang guards) is added;\n"
        "checking moves are extended one ply at depth>=1 nodes;")
    path.write_text(text)

    src_manifest = json.loads((SRC / "manifest.json").read_text())
    frozen = dict(src_manifest.get("sha256", {}))
    frozen["combined_search.py"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"candidate": "search_v2_mg_checkext_01", "base": "search_v2_nmp_mg_01",
                "change": "check extension +1 at depth>=1 "
                "(see CHECKEXT_DESIGN.md)",
                "sha256": frozen}
    (DST / "manifest.json").write_text(json.dumps(manifest, indent=1))

    ruff = subprocess.run([sys.executable, "-m", "ruff", "check", str(path)],
                          capture_output=True, text=True)
    print(ruff.stdout.strip() or ruff.stderr.strip())
    if ruff.returncode != 0:
        raise SystemExit("ruff failed on the patched file")
    print(f"built {DST}")


if __name__ == "__main__":
    main()
