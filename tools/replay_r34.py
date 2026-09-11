"""Fresh-process, cold-TT diagnostic replays; not tournament strength evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path)
    parser.add_argument('--fen')
    parser.add_argument('--clock', type=int)
    args = parser.parse_args()
    if args.engine:
        sys.path.insert(0, str(args.engine.resolve()))
        from engine import MilkyWayEngine
        from time_manager import allocate_time
        eng = MilkyWayEngine()
        board = chess.Board(args.fen)
        budget = allocate_time(args.clock, board.legal_moves.count())
        start = time.perf_counter()
        move = eng.choose_move(args.fen, args.clock)
        stats = eng.searcher.stats
        print(json.dumps({'move': move, 'san': board.san(chess.Move.from_uci(move)),
                          'score': stats.score, 'depth': stats.depth_reached,
                          'nodes': stats.nodes, 'pv': stats.pv,
                          'soft_ms': budget.soft_ms, 'hard_ms': budget.hard_ms,
                          'elapsed_ms': (time.perf_counter() - start) * 1000}))
        return
    with (ROOT / 'experiments/r34/aichessathon-round-34-sunfish.pgn').open() as stream:
        game = chess.pgn.read_game(stream)
    assert game is not None
    clock = 120000
    positions = []
    for node in game.mainline():
        before = node.parent.board()
        if before.turn == chess.BLACK:
            if before.fullmove_number in (28, 31, 35, 36, 43, 47):
                positions.append({'move_number': before.fullmove_number,
                                  'fen': before.fen(), 'clock_ms': clock,
                                  'played': node.san()})
            recorded_clock = node.clock()
            assert recorded_clock is not None
            clock = round(recorded_clock * 1000)
    records = []
    for position in positions:
        for label, directory in (
            ('checkpoint', ROOT / 'experiments/r34/checkpoint'),
            ('policy_tma', ROOT / 'versions/rc1_variants/rc1_tma'),
            ('ksc', ROOT / 'experiments/r34/ksc_candidate'),
        ):
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), '--engine', str(directory),
                 '--fen', str(position['fen']), '--clock', str(position['clock_ms'])],
                capture_output=True, text=True, check=True,
            )
            record = {**position, 'engine': label, **json.loads(result.stdout)}
            records.append(record)
            print(f"{position['move_number']} {label}: {record['san']} "
                  f"depth={record['depth']} score={record['score']}", flush=True)
    (ROOT / 'experiments/r34/replay.json').write_text(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
