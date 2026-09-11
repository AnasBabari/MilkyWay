"""Build the trained-weights firesock candidate (deterministic, reviewable).

Copies experiments/search_v2_nmp_01 -> experiments/search_v2_firesock_02,
then ONLY swaps weights/compact_value.npz for the guarded middlegame-trained
weights (compact_firesock_midgame_02). No book, no search/eval/clock change:
clean weights-only attribution vs NMP.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "experiments/search_v2_nmp_01"
DST = ROOT / "experiments/search_v2_firesock_02"
WEIGHTS = ROOT / "training/checkpoints/compact_firesock_midgame_02/compact_value.npz"


def main() -> None:
    if DST.exists():
        raise SystemExit(f"Refusing to overwrite {DST}")
    if not WEIGHTS.is_file():
        raise SystemExit("Trained weights missing")
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(WEIGHTS, DST / "weights" / "compact_value.npz")

    src_manifest = json.loads((SRC / "manifest.json").read_text())
    frozen = dict(src_manifest.get("sha256", {}))
    frozen["weights/compact_value.npz"] = hashlib.sha256(
        (DST / "weights" / "compact_value.npz").read_bytes()).hexdigest()
    manifest = {"candidate": "search_v2_firesock_02", "base": "search_v2_nmp_01",
                "change": "weights-only: middlegame outcome-trained compact "
                "residual (612k GM+SF7 positions, guarded, epoch 99)",
                "sha256": frozen}
    (DST / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"built {DST}")


if __name__ == "__main__":
    main()
