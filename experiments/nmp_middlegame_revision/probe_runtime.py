"""Evaluate one frozen runtime in its own process; no mixed module dependencies."""
import argparse
import json
import sys
import time
from pathlib import Path

import chess

parser = argparse.ArgumentParser()
parser.add_argument('--candidate', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(args.candidate.resolve()))
import combined_search as search  # noqa: E402
from compiled_eval import evaluate_array  # noqa: E402
from core import encode_board  # noqa: E402

import agent  # noqa: E402

rows = []
for game in ('r94_revision', 'r97_revision'):
    oracle = json.loads((ROOT / f'experiments/{game}/oracle_100k.json').read_text())
    positions = [r for r in oracle['moves'] if 20 <= r['ply'] <= 70
                 and abs(r['best_cp']) < 800 and len(chess.Board(r['fen']).piece_map()) > 10]
    positions.sort(key=lambda r: (-r['loss_cp'], r['ply']))
    for row in positions[:12]:
        board = chess.Board(row['fen'])
        result = search.search(board, seconds=20, max_depth=5)
        assert not result['aborted'], (game, row['ply'])
        assert chess.Move.from_uci(result['move']) in board.legal_moves
        assert board.fen() == row['fen']
        array, side, _, _ = encode_board(board)
        rows.append({'source': game, 'fen': row['fen'], 'ply': row['ply'],
                     'played': row['move'], 'old_oracle_best': row['best'],
                     'static_cp': int(evaluate_array(array, side)), **result})
print(f'{len(rows)} recorded middlegame probes completed', flush=True)
suite = json.loads((ROOT / 'experiments/search_v2/probe_suite_01.json').read_text())
fens = [p['fen'] for p in suite['positions']]
legal = []
for fen in fens[::4]:
    board = chess.Board(fen)
    result = search.search(board, seconds=0.15, max_depth=20)
    assert chess.Move.from_uci(result['move']) in board.legal_moves
    assert board.fen() == fen
    legal.append({'fen': fen, **result})
clocks = []
for fen in fens[:10]:
    for milliseconds in (50, 250, 1000):
        start = time.perf_counter()
        move = agent.get_move(fen, milliseconds)
        elapsed = time.perf_counter() - start
        assert chess.Move.from_uci(move) in chess.Board(fen).legal_moves
        assert elapsed < milliseconds / 1000, (milliseconds, elapsed)
        clocks.append({'clock_ms': milliseconds, 'elapsed_s': elapsed})
args.out.write_text(json.dumps({'candidate': str(args.candidate), 'middlegame': rows,
                                'legal_restored_probes': legal, 'clock_probes': clocks}, indent=2))
print('60 legality/restoration and 30 low-clock checks passed', flush=True)
