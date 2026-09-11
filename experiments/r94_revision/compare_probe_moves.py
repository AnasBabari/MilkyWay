"""Offline oracle comparison of changed choices, never included in the agent."""
import json
import sys
from pathlib import Path

import chess
import chess.engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from baselines.stockfish.agent import find_stockfish_binary  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / 'changed_choices_oracle.json'
assert not OUT.exists()
rows = []
binary = find_stockfish_binary()
assert binary
with chess.engine.SimpleEngine.popen_uci(binary) as engine:
    engine.configure({'Skill Level': 20, 'Threads': 1, 'Hash': 32})
    for category, field in (('probe', 'probe'), ('regression', 'result')):
        old = json.loads((HERE / f'baseline_{category}.json').read_text())['rows']
        new = json.loads((HERE / f'king_safety_{category}.json').read_text())['rows']
        assert len(old) == len(new)
        for before, after in zip(old, new, strict=True):
            assert before['fen'] == after['fen']
            a, b = before[field]['move'], after[field]['move']
            if a == b:
                continue
            board = chess.Board(before['fen'])
            values = []
            for move in (a, b):
                info = engine.analyse(board, chess.engine.Limit(nodes=200000),
                                      root_moves=[chess.Move.from_uci(move)], game=object())
                values.append(info['score'].pov(board.turn).score(mate_score=10000))
            row = {'category': category, 'fen': board.fen(), 'old_move': a, 'new_move': b,
                   'old_cp': values[0], 'new_cp': values[1], 'delta_cp': values[1] - values[0]}
            rows.append(row)
            print(json.dumps(row), flush=True)
OUT.write_text(json.dumps({'purpose': 'bounded offline diagnostic, not ground truth',
                           'nodes_per_forced_choice': 200000, 'rows': rows}, indent=2))
