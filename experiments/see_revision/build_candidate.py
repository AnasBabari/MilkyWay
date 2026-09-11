"""Create a frozen capture-ordering-only variant from NMP."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent
SRC = ROOT / 'experiments/search_v2_nmp_01'
DST = ROOT / 'experiments/search_v2_see_01'
manifest = json.loads((SRC / 'manifest.json').read_text())
assert not DST.exists()
for name, digest in manifest['sha256'].items():
    assert hashlib.sha256((SRC / name).read_bytes()).hexdigest() == digest
for name in manifest['sha256']:
    target = DST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC / name, target)
shutil.copyfile(LAB / 'capture_order.py', DST / 'capture_order.py')
path = DST / 'combined_search.py'
source = path.read_text()
source = source.replace('from compiled_eval import evaluate_array',
                        'from capture_order import VALUES, exchange_value\n'
                        'from compiled_eval import evaluate_array')
anchor = '        if quiet and move != preferred:\n'
assert source.count(anchor) == 1
source = source.replace(anchor,
'''        # A lower-valued victim does not guarantee a profitable exchange.
        # Demote losing captures behind quiet moves; retain every legal move.
        # Promotions and the TT move keep their existing priority.
        victim = abs(int(board[target]))
        attacker = abs(int(board[origin]))
        if (victim and move >> 12 == 0 and move != preferred
                and VALUES[attacker] > VALUES[victim]):
            stats[6] += 1
            if exchange_value(board, move, rights, ep) < 0:
                scores[i] -= 30000
                stats[7] += 1
''' + anchor)
source = source.replace('stats = np.zeros(6, dtype=np.int64)',
                        'stats = np.zeros(8, dtype=np.int64)')
source = source.replace('"null_cutoffs": int(stats[5])}',
                        '"null_cutoffs": int(stats[5]), "see_calls": int(stats[6]),\n'
                        '             "losing_captures_demoted": int(stats[7])}')
path.write_text(source, encoding='utf-8')
names = [*manifest['sha256'], 'capture_order.py']
frozen = {name: hashlib.sha256((DST / name).read_bytes()).hexdigest() for name in names}
assert [n for n in manifest['sha256'] if frozen[n] != manifest['sha256'][n]] == [
    'combined_search.py']
(DST / 'manifest.json').write_text(json.dumps({
    'candidate': DST.name, 'base': SRC.name, 'qualified': False,
    'change': 'Legal least-attacker exchange estimates for capture ordering only',
    'sha256': frozen}, indent=2))
print(DST, frozen['combined_search.py'])
