"""Freeze R34 controls and an independent KS-C evaluation candidate."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'experiments' / 'r34'
FILES = (
    'agent.py', 'constants.py', 'engine.py', 'engine_types.py', 'evaluation.py',
    'move_ordering.py', 'root_policy.py', 'search.py', 'time_manager.py',
    'transposition.py', 'weights/milkyway_policy.onnx',
)


def main() -> None:
    manifests = {}
    for name in ('checkpoint', 'ksc_candidate'):
        dest = OUT / name
        if dest.exists():
            raise SystemExit(f'Refusing to overwrite frozen snapshot: {dest}')
        for filename in FILES:
            target = dest / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / filename, target)
        if name == 'ksc_candidate':
            path = dest / 'evaluation.py'
            source = path.read_text()
            assert source.count('else MW_0_2_EVAL\n') == 1
            path.write_text(source.replace('else MW_0_2_EVAL\n', 'else MW_0_2_KS_C\n'))
        manifests[name] = {
            filename: hashlib.sha256((dest / filename).read_bytes()).hexdigest()
            for filename in FILES
        }
    (OUT / 'snapshots.json').write_text(json.dumps(manifests, indent=2))


if __name__ == '__main__':
    main()
