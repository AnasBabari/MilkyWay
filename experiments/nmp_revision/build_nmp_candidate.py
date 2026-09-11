"""Build the isolated null-move-pruning candidate (deterministic, reviewable).

Copies experiments/search_v2_combined_01 -> experiments/search_v2_nmp_01,
then applies ONLY the NMP change to combined_search.py:
  - has_non_pawn_material() guard (zugzwang safety: king+pawns-only skips)
  - null search at depth>=3, not in check, previous move real, static>=beta,
    beta below mate bound; R=2 (R=3 at depth>=6); fail-hard beta cutoff
  - no history update for the pass (documented accepted standard risk);
    null child gets flipped side, cleared EP, ticked halfmove clock
  - stats[5] counts null cutoffs; report dict extended; search() root passes
    null-allowed; all post-real-move recursions keep null allowed
Nothing else changes: same eval, movegen, TT, LMR, staged generation, clocks.
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
SRC = ROOT / "experiments/search_v2_combined_01"
DST = ROOT / "experiments/search_v2_nmp_01"

HELPER = '''

@njit(cache=False)
def has_non_pawn_material(board, side):
    # Zugzwang guard: with king+pawns only, passing is often best, so a
    # null-move cutoff would be unsound. Any N/B/R/Q of our colour allows it.
    for square in range(64):
        piece = int(board[square])
        if piece * side > 0 and abs(piece) >= 2 and abs(piece) <= 5:
            return True
    return False
'''

NMP_BLOCK = '''    if (depth >= 3 and not check and null_ok and beta < MATE - LIMIT
            and evaluate_array(board, side, coefficient) >= beta
            and has_non_pawn_material(board, side)):
        # Null-move pruning: verify the position is so good that even passing
        # keeps it above beta. No history update for the pass (standard):
        # a false repetition draw inside the null tree fails low (safe side)
        # except in vanishingly rare exact-3x key repeats with beta <= 0.
        null_depth = depth - 1 - (3 if depth >= 6 else 2)
        nvalue, _ = negamax(board, -side, rights, 0, halfmove + 1,
                            null_depth, -beta, -beta + 1, ply + 1, history,
                            history_count, stats, deadline, coefficient, 0,
                            tt_keys, tt_context, tt_data, killers, move_history,
                            lmr_enabled, False)
        if not stats[1] and -nvalue >= beta:
            stats[5] += 1
            return beta, preferred
'''


def main() -> None:
    if DST.exists():
        raise SystemExit(f"Refusing to overwrite {DST}")
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
    path = DST / "combined_search.py"
    text = path.read_text()

    # 1. helper after unpack_mate
    anchor = "@njit(cache=False)\ndef unpack_mate(value, ply):"
    assert anchor in text
    head, sep, tail = text.partition("\n\n\n@njit(cache=False)\ndef negamax(")
    assert sep, "negamax anchor missing"
    text = head + HELPER + sep + tail

    # 2. signature
    old_sig = ("def negamax(board, side, rights, ep, halfmove, depth, alpha, beta, ply,\n"
               "            history, history_count, stats, deadline, coefficient, preferred,\n"
               "            tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled):")
    new_sig = ("def negamax(board, side, rights, ep, halfmove, depth, alpha, beta, ply,\n"
               "            history, history_count, stats, deadline, coefficient, preferred,\n"
               "            tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,\n"
               "            null_ok):")
    assert old_sig in text
    text = text.replace(old_sig, new_sig)

    # 3. NMP block before best init (after TT probe)
    old_best = "    best = -MATE - 1\n    best_move = moves[0]\n"
    assert old_best in text
    text = text.replace(old_best, NMP_BLOCK + old_best, 1)

    # 4. the 4 post-real-move recursions + the root call keep null allowed.
    # (The null-search call itself ends 'lmr_enabled, False)' and is untouched.)
    old_tail = "tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled)"
    assert text.count(old_tail) == 5  # 4 recursions + root call
    new_tail_32 = ("tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,\n"
                   "                                True)")
    new_tail_30 = ("tt_keys, tt_context, tt_data, killers, move_history, lmr_enabled,\n"
                   "                               True)")
    pad32 = " " * 32
    text = text.replace(pad32 + old_tail, pad32 + new_tail_32)
    assert new_tail_32 in text
    pad30 = " " * 30
    text = text.replace(pad30 + old_tail, pad30 + new_tail_30)
    assert new_tail_30 in text
    assert old_tail not in text

    # 5. stats + report
    assert "stats = np.zeros(5, dtype=np.int64)" in text
    old_stats = "stats = np.zeros(5, dtype=np.int64)"
    new_stats = "stats = np.zeros(6, dtype=np.int64)"
    text = text.replace(old_stats, new_stats)
    old_rep = '"reductions": int(stats[3]), "reduction_researches": int(stats[4])}'
    new_rep = ('"reductions": int(stats[3]),\n'
               '             "reduction_researches": int(stats[4]),\n'
               '             "null_cutoffs": int(stats[5])}')
    assert old_rep in text
    text = text.replace(old_rep, new_rep)

    # 6. docstring note
    old_doc = "is preserved verbatim from the staged variant. "
    old_doc += "This is heuristic pruning;"
    new_doc = "is preserved verbatim from the staged variant. "
    new_doc += "Null-move pruning\n(R=2/3, conservative zugzwang guards) "
    new_doc += "is added; see has_non_pawn_material.\nThis is heuristic pruning;"
    text = text.replace(old_doc, new_doc)
    path.write_text(text)

    # 7. manifest: copy combined's, refresh changed hash
    src_manifest = json.loads((SRC / "manifest.json").read_text())
    frozen = dict(src_manifest.get("sha256", {}))
    frozen["combined_search.py"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"candidate": "search_v2_nmp_01", "base": "search_v2_combined_01",
                "change": "null-move pruning only (see NMP_DESIGN.md)",
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
