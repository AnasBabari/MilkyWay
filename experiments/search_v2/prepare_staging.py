"""Our exact quiescence generation experiment, isolated from playing agents."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> None:
    base = ROOT / "experiments/compiled_ordered_01"
    out = HERE / "staged_runtime_01"
    out.mkdir(exist_ok=False)
    manifest = json.loads((base / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        data = (base / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    core = (out / "core.py").read_text()
    before = ("def legal_moves(board, side, rights, ep):\n"
              "    moves, count = generate(board, side, rights, ep)")
    after = ("def legal_moves(board, side, rights, ep, captures_only=False, first_only=False):\n"
             "    moves, count = generate(board, side, rights, ep, captures_only)")
    assert core.count(before) == 1
    core = core.replace(before, after)
    before = "            kept += 1\n    return moves[:kept]"
    assert core.count(before) == 1
    core = core.replace(before, "            kept += 1\n"
                        "            if first_only:\n                break\n"
                        "    return moves[:kept]")
    (out / "core.py").write_text(core)
    source = (out / "ordered_search.py").read_text()
    before = ("    moves = legal_moves(board, side, rights, ep)\n"
              "    count = len(moves)\n"
              "    check = attacked(board, king_square(board, side), -side)")
    after = ("    check = attacked(board, king_square(board, side), -side)\n"
             "    if depth <= 0 and not check:\n"
             "        moves = legal_moves(board, side, rights, ep, True)\n"
             "        if len(moves) == 0:\n"
             "            # Preserve stalemate detection without validating every quiet move.\n"
             "            moves = legal_moves(board, side, rights, ep, False, True)\n"
             "    else:\n        moves = legal_moves(board, side, rights, ep)\n"
             "    count = len(moves)")
    assert source.count(before) == 1
    source = source.replace(before, after)
    (out / "staged_search.py").write_text(source)
    (out / "diagnostic_manifest.json").write_text(json.dumps({
        "purpose": "isolated staging experiment; not a selected baseline",
        "parent": str(base), "parent_sha256": manifest["sha256"],
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in out.glob("*.py")}}, indent=2))
    print(out)


if __name__ == "__main__":
    main()
