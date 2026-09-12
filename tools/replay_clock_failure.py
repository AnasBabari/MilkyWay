"""Replay recorded requests through the unchanged sandbox; diagnostic only."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any

import chess
import chess.pgn

from harness.sandbox import AgentFailure, local


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit('Refusing to overwrite diagnostic evidence')
    record = json.loads(args.record.read_text())
    game = chess.pgn.read_game(io.StringIO(record['pgn']))
    assert game is not None and not game.errors
    color = record['candidate_color'] == 'white'
    clock_ms = 120000
    board = game.board()
    requests: list[tuple[str, int, str | None]] = []
    for node in game.mainline():
        if board.turn == color:
            requests.append((board.fen(), clock_ms, node.move.uci()))
            clock = node.clock()
            assert clock is not None
            clock_ms = round(clock * 1000)
        board.push(node.move)
    assert board.turn == color
    requests.append((board.fen(), clock_ms, None))
    report: dict[str, Any] = {
        'purpose': 'Diagnostic replay, never tournament or qualification evidence',
        'record_sha256': hashlib.sha256(args.record.read_bytes()).hexdigest(),
        'agent': str(args.agent.resolve()),
        'runtime_sha256': {
            str(p.relative_to(args.agent)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in args.agent.rglob('*')
            if p.is_file() and p.suffix in {'.py', '.npz'}
        },
        'limitation': ('Different returned moves can cause history resynchronization; '
                       'no opponent think delays replayed.'),
        'requests': [],
    }
    agent = local(args.agent)
    try:
        started = time.perf_counter()
        agent.start(90)
        report['import_s'] = time.perf_counter() - started
        for fen, remaining, historical in requests:
            row: dict[str, Any] = {
                'fen': fen, 'time_left_ms': remaining, 'historical_move': historical,
            }
            started = time.perf_counter()
            try:
                move = agent.move(fen, remaining)
                row.update(move=move,
                           legal=chess.Move.from_uci(move) in chess.Board(fen).legal_moves)
            except AgentFailure as error:
                row['failure'] = error.reason
            row['elapsed_s'] = time.perf_counter() - started
            report['requests'].append(row)
            args.out.write_text(json.dumps(report, indent=2))
            print(json.dumps(row), flush=True)
            if 'failure' in row:
                break
    finally:
        agent.stop()
        report['stderr'] = agent.stderr_log
        args.out.write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
