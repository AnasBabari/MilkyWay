"""Functional probes and measured search work; not strength qualification."""
import importlib.util
import json
import sys
import time
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'experiments/search_v2_delta_01'))
import combined_search as candidate  # noqa: E402

import agent  # noqa: E402

spec = importlib.util.spec_from_file_location(
    'baseline_search', ROOT / 'experiments/search_v2_nmp_01/combined_search.py')
baseline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = baseline
spec.loader.exec_module(baseline)
baseline.search(chess.Board(), seconds=0, max_depth=1)
print('Both runtimes compiled', flush=True)
suite = json.loads((ROOT / 'experiments/search_v2/probe_suite_01.json').read_text())
fens = [p['fen'] for p in suite['positions']]
rows = []
for fen in fens[::4]:
    board = chess.Board(fen)
    result = candidate.search(board, seconds=0.15, max_depth=20)
    assert chess.Move.from_uci(result['move']) in board.legal_moves
    assert board.fen() == fen
    rows.append({'fen': fen, **result})
assert sum(r['delta_prunes'] for r in rows) > 0, 'New mechanism never engaged'
print('60 legal/restored probes; pruning engaged', flush=True)
comparisons = []
for fen in fens[::24]:
    pair = {'fen': fen}
    for name, mod in (('nmp', baseline), ('delta', candidate)):
        result = mod.search(chess.Board(fen), seconds=10, max_depth=4)
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
report = {'qualified': False, 'legal_restored_probes': rows,
          'fixed_depth_comparisons': comparisons, 'clock_probes': clocks,
          'delta_prunes': sum(r['delta_prunes'] for r in rows)}
(LAB / 'verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps({'legal_probes': len(rows), 'clock_probes': len(clocks),
                  'delta_prunes': report['delta_prunes'],
                  'fixed_depth_nodes_nmp': sum(r['nmp']['nodes'] for r in comparisons),
                  'fixed_depth_nodes_delta': sum(r['delta']['nodes'] for r in comparisons)}),
      flush=True)
