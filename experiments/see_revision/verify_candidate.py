"""Check exchange estimates against python-chess, then search and clock probes."""
import importlib.util
import json
import random
import sys
import time
from pathlib import Path

import chess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'experiments/search_v2_see_01'))
import combined_search as candidate  # noqa: E402
from capture_order import VALUES, exchange_value  # noqa: E402
from core import encode_board  # noqa: E402

import agent  # noqa: E402


def capture_gain(board, move):
    victim = 1 if board.is_en_passant(move) else (board.piece_type_at(move.to_square) or 0)
    return VALUES[victim] + (VALUES[move.promotion] - 100 if move.promotion else 0)


def slow_recaptures(board, target):
    captures = [m for m in board.legal_moves if m.to_square == target and board.is_capture(m)
                and m.promotion in (None, chess.QUEEN)]
    if not captures:
        return 0
    move = min(captures, key=lambda m: (VALUES[board.piece_type_at(m.from_square)],
                                       m.from_square))
    gain = capture_gain(board, move)
    board.push(move)
    result = max(0, gain - slow_recaptures(board, target))
    board.pop()
    return result


def verify_exchange(board, move):
    fen = board.fen()
    array, _, rights, ep = encode_board(board)
    before = array.copy()
    encoded = move.from_square | (move.to_square << 6) | ((move.promotion or 0) << 12)
    actual = int(exchange_value(array, encoded, rights, ep))
    gain = capture_gain(board, move)
    board.push(move)
    expected = gain - slow_recaptures(board, move.to_square)
    board.pop()
    assert actual == expected, (fen, move.uci(), actual, expected)
    assert np.array_equal(before, array) and board.fen() == fen
    return {'fen': fen, 'move': move.uci(), 'value': actual}


curated = [
    ('4k3/8/4p3/3p4/8/8/8/3QK3 w - - 0 1', 'd1d5'),
    ('4k3/4p3/3p4/8/8/8/8/3QR1K1 w - - 0 1', 'd1d6'),
    ('4k3/8/4p3/3p4/8/8/3R4/3RK3 w - - 0 1', 'd2d5'),
    ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6'),
    ('k6r/6P1/8/8/8/8/8/4K3 w - - 0 1', 'g7h8q'),
    ('4k3/8/8/8/8/8/3p4/4K3 w - - 0 1', 'e1d2'),
    ('8/8/4k3/3p4/2P5/8/3R4/4K3 w - - 0 1', 'd2d5'),
]
exchanges = []
for fen, uci in curated:
    board = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    assert board.is_valid() and move in board.legal_moves, fen
    exchanges.append(verify_exchange(board, move))
randomizer = random.Random(20260910)
board = chess.Board()
while len(exchanges) < 306:
    if board.is_game_over() or board.ply() > 180:
        board.reset()
    captures = sorted([m for m in board.legal_moves if board.is_capture(m)], key=lambda m: m.uci())
    for move in captures[:8]:
        exchanges.append(verify_exchange(board, move))
        if len(exchanges) == 306:
            break
    board.push(randomizer.choice(list(board.legal_moves)))
print('306 exchange oracle checks passed, including pins/x-rays/EP/promotion/king', flush=True)

spec = importlib.util.spec_from_file_location(
    'baseline_search', ROOT / 'experiments/search_v2_nmp_01/combined_search.py')
baseline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = baseline
spec.loader.exec_module(baseline)
baseline.search(chess.Board(), seconds=0, max_depth=1)
suite = json.loads((ROOT / 'experiments/search_v2/probe_suite_01.json').read_text())
fens = [p['fen'] for p in suite['positions']]
rows = []
for fen in fens[::4]:
    board = chess.Board(fen)
    result = candidate.search(board, seconds=0.15, max_depth=20)
    assert chess.Move.from_uci(result['move']) in board.legal_moves
    assert board.fen() == fen
    rows.append({'fen': fen, **result})
assert sum(r['losing_captures_demoted'] for r in rows) > 0
comparisons = []
for fen in fens[::24]:
    pair = {'fen': fen}
    for name, mod in (('nmp', baseline), ('see', candidate)):
        result = mod.search(chess.Board(fen), seconds=15, max_depth=4)
        assert not result['aborted']
        pair[name] = result
    comparisons.append(pair)
clocks = []
for fen in fens[:10]:
    for milliseconds in (50, 250, 1000):
        start = time.perf_counter()
        move = agent.get_move(fen, milliseconds)
        elapsed = time.perf_counter() - start
        assert chess.Move.from_uci(move) in chess.Board(fen).legal_moves
        assert elapsed < milliseconds / 1000, (milliseconds, elapsed)
        clocks.append({'clock_ms': milliseconds, 'elapsed_s': elapsed})
report = {'qualified': False, 'exchange_oracle_checks': exchanges,
          'legal_restored_probes': rows, 'fixed_depth_comparisons': comparisons,
          'clock_probes': clocks}
(LAB / 'verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps({'legal_probes': len(rows), 'clock_probes': len(clocks),
                  'demotions': sum(r['losing_captures_demoted'] for r in rows),
                  'nodes_nmp': sum(r['nmp']['nodes'] for r in comparisons),
                  'nodes_see': sum(r['see']['nodes'] for r in comparisons),
                  'seconds_nmp': sum(r['nmp']['elapsed_s'] for r in comparisons),
                  'seconds_see': sum(r['see']['elapsed_s'] for r in comparisons)}), flush=True)
