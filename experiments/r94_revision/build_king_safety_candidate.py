"""One-component king-exposure experiment; no move or opening lookup data."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'experiments/search_v2_combined_01'
OUT = ROOT / 'experiments/r94_king_safety_01'
manifest = json.loads((BASE / 'manifest.json').read_text())
OUT.mkdir(exist_ok=False)
for name, expected in manifest['sha256'].items():
    raw = (BASE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    target = OUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

source = OUT / 'compiled_eval.py'
code = source.read_text()
helper = '''
@njit(cache=False)
def exposed_king_penalty(board, color):
    """Penalize a central king with open approach files against heavy pieces.

    This is a general positional feature, inactive without an enemy queen,
    with lower weight after the enemy rooks have been exchanged.
    """
    king = -1
    queen = False
    rooks = 0
    for square in range(64):
        piece = int(board[square])
        if piece == color * 6:
            king = square
        elif piece == -color * 5:
            queen = True
        elif piece == -color * 4:
            rooks += 1
    if king < 0 or not queen:
        return 0
    file = king % 8
    if file < 3 or file > 4:
        return 0
    rank = king // 8
    relative_rank = rank if color == 1 else 7 - rank
    danger = 20 + min(relative_rank, 3) * 15
    for f in range(file - 1, file + 2):
        protected = False
        for step in (1, 2):
            r = rank + color * step
            if 0 <= r < 8 and board[r * 8 + f] == color:
                protected = True
        if not protected:
            danger += 25
    return danger * (2 + min(rooks, 2)) // 4

'''
marker = '@njit(cache=False)\ndef evaluate_array'
code = code.replace(marker, helper + marker, 1)
code = code.replace('    if coefficient == 0:',
                    '    classical += side * (exposed_king_penalty(board, -1)\n'
                    '                         - exposed_king_penalty(board, 1))\n'
                    '    if coefficient == 0:', 1)
source.write_text(code)
hashes = {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
          for name in manifest['sha256']}
assert [name for name in hashes if hashes[name] != manifest['sha256'][name]] == ['compiled_eval.py']
(OUT / 'manifest.json').write_text(json.dumps({
    'status': 'experimental; not qualified', 'parent': str(BASE),
    'parent_sha256': manifest['sha256'], 'sha256': hashes,
    'mechanism': 'central king exposure against enemy queen/rooks',
    'motivation': 'R94 missed queenside castling; requires independent regression testing',
}, indent=2))
print(OUT)
