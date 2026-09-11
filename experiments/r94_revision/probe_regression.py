"""Fixed pre-existing suite and interface checks for an isolated runtime."""
import hashlib
import json
import sys
import time
from pathlib import Path

import chess

runtime = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
assert not out.exists()
sys.path.insert(0, str(runtime))
started = time.perf_counter()
import agent  # noqa: E402,I001
import compiled_eval  # noqa: E402
from combined_search import search  # noqa: E402
from compiled_eval import evaluate_array  # noqa: E402
from core import encode_board  # noqa: E402

init_s = time.perf_counter() - started
root = Path(__file__).resolve().parents[2]
suite = root / 'experiments/search_v2/probe_suite_01.json'
data = json.loads(suite.read_text(encoding='utf-8-sig'))
positions = (data['positions'] if isinstance(data, dict) else data)[::4]
rows = []
symmetry = []
for item in positions:
    board = chess.Board(item['fen'])
    before = board.fen()
    result = search(board, seconds=0.15, soft_seconds=0.15, max_depth=40)
    assert board.fen() == before
    assert chess.Move.from_uci(result['move']) in board.legal_moves
    array, side, _, _ = encode_board(board)
    mirrored, other, _, _ = encode_board(board.mirror())
    symmetry.append({'id': item.get('id'), 'delta': int(
        evaluate_array(array, side) - evaluate_array(mirrored, other))})
    if hasattr(compiled_eval, 'exposed_king_penalty'):
        penalty = compiled_eval.exposed_king_penalty
        assert penalty(array, 1) == penalty(mirrored, -1)
        assert penalty(array, -1) == penalty(mirrored, 1)
    rows.append({'id': item.get('id'), 'fen': before, 'result': result})
clock_rows = []
for item in positions[:20]:
    for clock in (50, 250, 1000):
        started = time.perf_counter()
        move = agent.get_move(item['fen'], clock)
        elapsed = time.perf_counter() - started
        assert chess.Move.from_uci(move) in chess.Board(item['fen']).legal_moves
        assert elapsed * 1000 < clock, (item['id'], clock, elapsed)
        clock_rows.append({'id': item.get('id'), 'clock_ms': clock, 'elapsed_s': elapsed})
out.write_text(json.dumps({'runtime': str(runtime), 'suite_sha256':
                          hashlib.sha256(suite.read_bytes()).hexdigest(),
                          'import_s': init_s, 'rows': rows, 'clock_checks': clock_rows,
                          'existing_evaluation_symmetry_deltas': symmetry,
                          'new_feature_symmetry_checked':
                          hasattr(compiled_eval, 'exposed_king_penalty'),
                          'legality_board_restoration_passed': True}, indent=2))
print(json.dumps({'runtime': str(runtime), 'positions': len(rows),
                  'clock_checks': len(clock_rows), 'import_s': init_s}), flush=True)
