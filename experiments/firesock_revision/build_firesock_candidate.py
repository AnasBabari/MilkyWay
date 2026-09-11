"""Build the isolated firesock candidate (deterministic, reviewable).

Copies experiments/search_v2_nmp_01 -> experiments/search_v2_firesock_01,
then ONLY:
  1. adds weights/firesock_book.bin (own-human-games Polyglot book), and
  2. patches agent.py to probe the book (deterministic top weight) for
     ply < 30, falling back to normal search on miss or error.
No search/eval/clock change. Book moves update board+keys like searched moves.
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
SRC = ROOT / "experiments/search_v2_nmp_01"
DST = ROOT / "experiments/search_v2_firesock_01"
BOOK = HERE / "firesock_book.bin"
MAX_BOOK_PLY = 30

IMPORT_PATCH = '''import pathlib
import time

import chess
import chess.polyglot
from combined_search import position_key, search
from core import encode_board
'''

BOOK_INIT = '''
try:
    _book = chess.polyglot.open_reader(
        str(pathlib.Path(__file__).resolve().parent / "weights" / "firesock_book.bin"))
except OSError:
    _book = None
'''

BOOK_PROBE = '''    assert _board is not None
    if _book is not None and _board.ply() < 30:
        # Own-human-games opening book: deterministic top weight, validated.
        pick = None
        for entry in _book.find_all(_board, minimum_weight=1):
            if pick is None or entry.weight > pick.weight:
                pick = entry
        if pick is not None and pick.move in legal:
            _board.push(pick.move)
            _keys.append(_key(_board))
            return pick.move.uci()
    best = min(legal, key=lambda m: m.uci())
'''


def main() -> None:
    if DST.exists():
        raise SystemExit(f"Refusing to overwrite {DST}")
    if not BOOK.is_file():
        raise SystemExit("Book missing: run build_firesock_book.py first")
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(BOOK, DST / "weights" / "firesock_book.bin")

    path = DST / "agent.py"
    text = path.read_text()
    old_import = ("import time\n\nimport chess\n"
                  "from combined_search import position_key, search\n"
                  "from core import encode_board\n")
    assert old_import in text
    text = text.replace(old_import, IMPORT_PATCH)
    anchor = "from time_manager import allocate_time\n"
    assert anchor in text
    text = text.replace(anchor, anchor + BOOK_INIT, 1)
    old_sync = "    assert _board is not None\n    best = min(legal, key=lambda m: m.uci())\n"
    assert old_sync in text
    text = text.replace(old_sync, BOOK_PROBE, 1)
    path.write_text(text)

    src_manifest = json.loads((SRC / "manifest.json").read_text())
    frozen = dict(src_manifest.get("sha256", {}))
    frozen["agent.py"] = hashlib.sha256(path.read_bytes()).hexdigest()
    frozen["weights/firesock_book.bin"] = hashlib.sha256(
        (DST / "weights" / "firesock_book.bin").read_bytes()).hexdigest()
    manifest = {"candidate": "search_v2_firesock_01", "base": "search_v2_nmp_01",
                "change": "own-human-games Polyglot book probe, ply<30 (see FIRESOCK_DESIGN.md)",
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
