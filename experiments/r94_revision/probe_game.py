"""Probe a supplied rated game at identical budgets, preserving runtime identity."""
import hashlib
import io
import json
import sys
import time
from pathlib import Path

import chess
import chess.pgn

runtime = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
assert not out.exists()
sys.path.insert(0, str(runtime))
started = time.perf_counter()
import agent  # noqa: E402,F401,I001
from combined_search import search  # noqa: E402

init_s = time.perf_counter() - started
game_path = Path(__file__).parent / 'rated94.json'
game = chess.pgn.read_game(io.StringIO(json.loads(game_path.read_text())['pgn']))
assert game is not None
board = game.board()
rows = []
for node in game.mainline():
    if board.turn and board.fullmove_number in (10, 14, 18, 20, 21, 22, 26, 28):
        result = search(board, seconds=4.0, soft_seconds=2.0, max_depth=40)
        assert chess.Move.from_uci(result['move']) in board.legal_moves
        rows.append({'ply': board.ply(), 'fen': board.fen(),
                     'played': node.move.uci(), 'probe': result})
        out.write_text(json.dumps({'runtime': str(runtime), 'import_s': init_s,
                                  'runtime_sha256': {
                                      p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in runtime.glob('*.py')},
                                  'rows': rows}, indent=2))
        print(json.dumps(rows[-1]), flush=True)
    board.push(node.move)
