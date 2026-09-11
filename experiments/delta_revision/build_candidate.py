"""Freeze a one-mechanism delta-pruning experiment from the NMP champion."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'experiments/search_v2_nmp_01'
DST = ROOT / 'experiments/search_v2_delta_01'

manifest = json.loads((SRC / 'manifest.json').read_text())
assert not DST.exists(), 'Never mutate an existing frozen variant'
for name, digest in manifest['sha256'].items():
    assert hashlib.sha256((SRC / name).read_bytes()).hexdigest() == digest, name
for name in manifest['sha256']:
    target = DST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC / name, target)

path = DST / 'combined_search.py'
source = path.read_text()
helper = '''@njit(cache=False)
def delta_position_safe(board):
    # Keep sparse endings and imminent pawn promotions fully searched.
    pieces = 0
    for square in range(64):
        piece = int(board[square])
        pieces += piece != 0
        if (piece == 1 and square // 8 >= 5) or (piece == -1 and square // 8 <= 2):
            return False
    return pieces > 10


'''
anchor = '@njit(cache=False)\ndef negamax('
assert source.count(anchor) == 1
source = source.replace(anchor, helper + anchor)
anchor = '    best_move = moves[0]\n'
assert source.count(anchor) == 1
source = source.replace(anchor, anchor + '    stand_pat = 0\n    delta_safe = False\n')
anchor = '        best = evaluate_array(board, side, coefficient)\n'
assert source.count(anchor) == 1
source = source.replace(anchor, anchor + '        stand_pat = best\n'
                        '        delta_safe = delta_position_safe(board)\n')
anchor = '        undo = make_move(board, move, rights, ep)\n'
assert source.count(anchor) == 1
source = source.replace(anchor, '''        victim = abs(int(board[target]))
        if pawn and target == ep and victim == 0:
            victim = 1
        undo = make_move(board, move, rights, ep)
        # This is a heuristic, not an upper bound on tactical gain. Preserve
        # checks, promotions, mate windows, late endings and advanced pawns.
        # Generous material estimates plus 250cp allow positional improvement.
        if (depth <= 0 and not check and delta_safe and capture and promotion == 0
                and abs(alpha) < MATE - LIMIT
                and stand_pat + (0, 120, 400, 420, 650, 1200, 0)[victim] + 250 < alpha
                and not attacked(board, king_square(board, -side), side)):
            unmake_move(board, move, undo)
            stats[6] += 1
            continue
''')
source = source.replace('stats = np.zeros(6, dtype=np.int64)',
                        'stats = np.zeros(7, dtype=np.int64)')
source = source.replace('"null_cutoffs": int(stats[5])}',
                        '"null_cutoffs": int(stats[5]), "delta_prunes": int(stats[6])}')
path.write_text(source, encoding='utf-8')
frozen = {name: hashlib.sha256((DST / name).read_bytes()).hexdigest()
          for name in manifest['sha256']}
changed = [name for name in frozen if frozen[name] != manifest['sha256'][name]]
assert changed == ['combined_search.py'], changed
(DST / 'manifest.json').write_text(json.dumps({
    'candidate': DST.name, 'base': SRC.name,
    'change': 'Conservative quiescence delta pruning only; 250cp margin',
    'qualified': False, 'sha256': frozen,
}, indent=2))
print(DST, frozen['combined_search.py'])
