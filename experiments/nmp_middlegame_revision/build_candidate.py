"""Correct NMP's edge-file pawn attack mapping; preserve its search and weights."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'experiments/search_v2_nmp_01'
DST = ROOT / 'experiments/search_v2_nmp_mg_01'
assert not DST.exists(), 'Never mutate a frozen candidate'
manifest = json.loads((SRC / 'manifest.json').read_text())
for name, digest in manifest['sha256'].items():
    assert hashlib.sha256((SRC / name).read_bytes()).hexdigest() == digest, name
for name in manifest['sha256']:
    target = DST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC / name, target)

for name in ('fast_eval.py', 'evaluation.py'):
    path = DST / name
    text = path.read_text()
    if name == 'fast_eval.py':
        pairs = [
            ('ubp', '0x7F7F7F7F7F7F7F7F', '>>', 9, '0xFEFEFEFEFEFEFEFE'),
            ('ubp', '0xFEFEFEFEFEFEFEFE', '>>', 7, '0x7F7F7F7F7F7F7F7F'),
            ('uwp', '0x7F7F7F7F7F7F7F7F', '<<', 7, '0xFEFEFEFEFEFEFEFE'),
            ('uwp', '0xFEFEFEFEFEFEFEFE', '<<', 9, '0x7F7F7F7F7F7F7F7F'),
        ]
        for piece, old_mask, shift, amount, new_mask in pairs:
            old = f'(({piece} & np.uint64({old_mask})) {shift} np.uint64({amount}))'
            new = f'(({piece} & np.uint64({new_mask})) {shift} np.uint64({amount}))'
            assert text.count(old) == 1, old
            text = text.replace(old, new)
    else:
        for old_mask, shift, amount, new_mask in (
            ('0x7F7F7F7F7F7F7F7F', '<<', 7, '0xFEFEFEFEFEFEFEFE'),
            ('0xFEFEFEFEFEFEFEFE', '<<', 9, '0x7F7F7F7F7F7F7F7F'),
            ('0x7F7F7F7F7F7F7F7F', '>>', 9, '0xFEFEFEFEFEFEFEFE'),
            ('0xFEFEFEFEFEFEFEFE', '>>', 7, '0x7F7F7F7F7F7F7F7F'),
        ):
            old = f'((enemy_pawns_mask & {old_mask}) {shift} {amount})'
            new = f'((enemy_pawns_mask & {new_mask}) {shift} {amount})'
            assert text.count(old) == 1, old
            text = text.replace(old, new)
    path.write_text(text, encoding='utf-8')

frozen = {name: hashlib.sha256((DST / name).read_bytes()).hexdigest()
          for name in manifest['sha256']}
changed = [n for n in frozen if frozen[n] != manifest['sha256'][n]]
assert set(changed) == {'fast_eval.py', 'evaluation.py'}
(DST / 'manifest.json').write_text(json.dumps({
    'candidate': DST.name, 'base': SRC.name, 'qualified': False,
    'change': 'Correct edge-file pawn attack masks in C king-safety evaluation',
    'sha256': frozen}, indent=2))
print(DST, changed)
