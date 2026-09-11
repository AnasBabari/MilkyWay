"""Build the isolated Syzygy endgame-table candidate (deterministic, reviewable).

Copies experiments/search_v2_nmp_01 -> experiments/search_v2_syzygy_01,
then ONLY:
  1. adds weights/syzygy/*.rtbw|*.rtbz (official 3-man tables, SHA-verified
     against lichess checksums at download), and
  2. patches agent.py to probe the tables at the root when <=3 pieces remain:
     decisive WDL with feasible DTZ -> DTZ-optimal move; otherwise normal
     search. Missing tables or probe errors fall back to search silently.
No search/eval/clock change.
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
DST = ROOT / "experiments/search_v2_syzygy_01"
TABLES = ROOT / "experiments/syzygy_revision/tables"

IMPORT_PATCH = '''import pathlib
import time

import chess
import chess.syzygy
from combined_search import position_key, search
from core import encode_board
'''

TB_INIT = '''
try:
    _tables = chess.syzygy.open_tablebase(
        str(pathlib.Path(__file__).resolve().parent / "weights" / "syzygy"))
except OSError:
    _tables = None
'''

TB_PROBE = '''    assert _board is not None
    if _tables is not None and len(_board.piece_map()) <= 3:
        # Perfect endgame knowledge: decisive WDL with feasible DTZ plays
        # the fastest-progress move; anything else falls back to search.
        try:
            wdl = _tables.probe_wdl(_board)
        except (KeyError, ValueError):
            wdl = 0
        if abs(wdl) == 2:
            choice = None
            choice_dtz = None
            for move in legal:
                _board.push(move)
                try:
                    dtz = _tables.probe_dtz(_board)
                except (KeyError, ValueError):
                    dtz = None
                _board.pop()
                if dtz is None:
                    continue
                if choice is None or (wdl == 2 and dtz < choice_dtz) or (
                        wdl == -2 and dtz > choice_dtz):
                    choice, choice_dtz = move, dtz
            if choice is not None and choice_dtz is not None and (
                    choice_dtz + _board.halfmove_clock < 100):
                _board.push(choice)
                _keys.append(_key(_board))
                return choice.uci()
    best = min(legal, key=lambda m: m.uci())
'''


def main() -> None:
    if DST.exists():
        raise SystemExit(f"Refusing to overwrite {DST}")
    tables = sorted(TABLES.glob("*.rtbw")) + sorted(TABLES.glob("*.rtbz"))
    assert tables, "download 3-man tables first"
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
    tbdir = DST / "weights" / "syzygy"
    tbdir.mkdir(parents=True, exist_ok=True)
    for src in tables:
        shutil.copyfile(src, tbdir / src.name)

    path = DST / "agent.py"
    text = path.read_text()
    old_import = ("import time\n\nimport chess\n"
                  "from combined_search import position_key, search\n"
                  "from core import encode_board\n")
    assert old_import in text
    text = text.replace(old_import, IMPORT_PATCH)
    anchor = "from time_manager import allocate_time\n"
    assert anchor in text
    text = text.replace(anchor, anchor + TB_INIT, 1)
    old_sync = "    assert _board is not None\n    best = min(legal, key=lambda m: m.uci())\n"
    assert old_sync in text
    text = text.replace(old_sync, TB_PROBE, 1)
    path.write_text(text)

    src_manifest = json.loads((SRC / "manifest.json").read_text())
    frozen = dict(src_manifest.get("sha256", {}))
    frozen["agent.py"] = hashlib.sha256(path.read_bytes()).hexdigest()
    for src in tables:
        rel = "weights/syzygy/" + src.name
        frozen[rel] = hashlib.sha256((tbdir / src.name).read_bytes()).hexdigest()
    manifest = {"candidate": "search_v2_syzygy_01", "base": "search_v2_nmp_01",
                "change": "Syzygy 3-man root probe (see SYZYGY_DESIGN.md)",
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
