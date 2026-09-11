"""Independent pawn-map and isolated king-safety oracle checks."""
import ast
import json
import sys
from pathlib import Path

import chess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent
CANDIDATE = ROOT / 'experiments/search_v2_nmp_mg_01'
sys.path.insert(0, str(CANDIDATE))
import fast_eval as fe  # noqa: E402


def source_maps(path):
    tree = ast.parse(path.read_text())
    values = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'patt' for t in node.targets)]
    assert len(values) == 2
    order = (False, True) if path.name == 'fast_eval.py' else (True, False)
    return {color: compile(ast.Expression(value), str(path), 'eval')
            for color, value in zip(order, values, strict=True)}


maps = {}
for label, directory in (('nmp', ROOT / 'experiments/search_v2_nmp_01'),
                         ('refined', CANDIDATE)):
    maps[label] = {}
    for name in ('evaluation.py', 'fast_eval.py'):
        expressions = source_maps(directory / name)
        wrong = []
        for color in (True, False):
            for square in range(64):
                pawn = 1 << square
                value = int(eval(expressions[color], {'np': np, 'uwp': np.uint64(pawn),
                                'ubp': np.uint64(pawn), 'enemy_pawns_mask': pawn})) & chess.BB_ALL
                expected = chess.BB_PAWN_ATTACKS[color][square]
                if value != expected:
                    wrong.append({'color': color, 'square': chess.square_name(square),
                                  'actual': value, 'expected': expected})
        maps[label][name] = wrong
assert all(not wrong for wrong in maps['refined'].values())
assert all(maps['nmp'].values()), 'Original bug did not reproduce'
print('All 256 candidate pawn mappings pass; original mismatches:',
      {n: len(w) for n, w in maps['nmp'].items()}, flush=True)

params = np.zeros(576, dtype=np.int64)
params[37], params[38], params[39], params[42] = -100, -100000, 1000000, 2
params[43:48] = [24, 1, 1, 2, 4]


def isolated(board):
    bits = [np.uint64(board.pieces_mask(kind, color))
            for color in (chess.WHITE, chess.BLACK) for kind in range(1, 7)]
    return fe._eval_kernel(*bits, 1 if board.turn else 0, params, fe.RAYS,
                           fe.KNIGHT_ATTACKS, fe.KING_ATTACKS, fe.PAWN_ATTACKS,
                           fe.PASSER_MASKS, fe.WHITE_PST_SQ, fe._BISHOP_DIRS_ARR,
                           fe._ROOK_DIRS_ARR, fe._ALL_DIRS_ARR)


def oracle(board):
    safety = {}
    for color in (chess.WHITE, chess.BLACK):
        king = board.king(color)
        zone = chess.BB_KING_ATTACKS[king] | (1 << king)
        enemy_attacks = 0
        for kind in range(1, 6):
            for square in board.pieces(kind, not color):
                enemy_attacks |= board.attacks_mask(square)
        units = (enemy_attacks & zone).bit_count()
        queens = board.pieces(chess.QUEEN, not color)
        if queens:
            distance = min(abs(chess.square_file(q) - chess.square_file(king))
                           + abs(chess.square_rank(q) - chess.square_rank(king)) for q in queens)
            units += max(0, 4 - distance)
        safety[color] = -100 * units
    mg = safety[True] - safety[False]
    eg = int(mg * 0.2)
    phase = min(24, sum(len(board.pieces(kind, color)) * weight
                       for color in (True, False) for kind, weight in ((2, 1), (3, 1),
                                                                     (4, 2), (5, 4))))
    score = int(mg * (phase / 24) + eg * (1 - phase / 24))
    return score if board.turn else -score


suite = json.loads((ROOT / 'experiments/search_v2/probe_suite_01.json').read_text())
fens = [p['fen'] for p in suite['positions']]
for fen in fens:
    board = chess.Board(fen)
    for position in (board, board.mirror()):
        actual, expected = isolated(position), oracle(position)
        assert actual == expected, (position.fen(), actual, expected)
report = {'source_mapping_checks': 256, 'isolated_kernel_checks': len(fens) * 2,
          'original_mapping_errors': maps['nmp'], 'corrected_mapping_errors': maps['refined']}
(LAB / 'mapping_verification.json').write_text(json.dumps(report, indent=2))
print('480 isolated king-safety evaluations match python-chess geometry', flush=True)
