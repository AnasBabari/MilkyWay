"""Exercise actual get_move allocation at the rated game's critical clock."""
import json
import sys
import time
from pathlib import Path

import chess

runtime = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(runtime))
import agent  # noqa: E402

out = Path(sys.argv[2]).resolve()
assert not out.exists()
rows = json.loads((Path(__file__).parent / 'oracle_100k.json').read_text())['moves']
results = []
for row in rows:
    if row['ply'] not in (18, 26, 50):
        continue
    clock = round(row['clock_before_s'] * 1000)
    started = time.perf_counter()
    move = agent.get_move(row['fen'], clock)
    elapsed = time.perf_counter() - started
    assert chess.Move.from_uci(move) in chess.Board(row['fen']).legal_moves
    assert elapsed < clock / 1000
    results.append({'ply': row['ply'], 'clock_ms': clock, 'move': move,
                    'elapsed_s': elapsed, 'search': agent._last_search})
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results[-1]), flush=True)
