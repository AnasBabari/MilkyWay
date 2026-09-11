"""Playing-interface history, legal fallback, warmup and clock checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import chess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--runtime", type=Path, default=Path(__file__).parent)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
if args.out.exists():
    raise SystemExit("Refuse to overwrite a verification report")
sys.path.insert(0, str(args.runtime.resolve()))
started = time.perf_counter()
import agent  # noqa: E402

IMPORT_SECONDS = time.perf_counter() - started


def main():
    assert IMPORT_SECONDS < 90, IMPORT_SECONDS
    rng = random.Random(20260917)
    board = chess.Board()
    previous_count = 0
    reset = True
    maximum = 0.0
    for _ in range(80):
        if board.is_game_over():
            board = chess.Board()
            reset = True
        before = board.fen()
        t = time.perf_counter()
        move = chess.Move.from_uci(agent.get_move(before, 250))
        elapsed = time.perf_counter() - t
        maximum = max(maximum, elapsed)
        assert elapsed < 0.20, elapsed
        assert move in board.legal_moves
        board.push(move)
        assert agent._board.fen() == board.fen()
        assert len(agent._keys) == (2 if reset else previous_count + 2)
        previous_count = len(agent._keys)
        reset = False
        if board.is_game_over():
            continue
        board.push(rng.choice(list(board.legal_moves)))
    # A fresh unrelated FEN resets rather than fabricating prior repetitions.
    fresh = chess.Board("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
    move = chess.Move.from_uci(agent.get_move(fresh.fen(), 1))
    assert move in fresh.legal_moves and len(agent._keys) == 2
    # One full-clock allocation probe is a timing test, not a tournament result.
    fresh = chess.Board()
    t = time.perf_counter()
    move = chess.Move.from_uci(agent.get_move(fresh.fen(), 120000))
    elapsed = time.perf_counter() - t
    assert move in fresh.legal_moves and elapsed < 7.0, elapsed
    root = args.runtime.resolve()
    result = {"import_s": IMPORT_SECONDS, "low_clock_moves": 80,
              "max_250ms_clock_move_s": maximum, "full_clock_probe_s": elapsed,
              "full_clock_search": agent._last_search,
              "history_extension_and_reset": True,
              "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in root.glob("*.py")}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "sha256"}, indent=2))


if __name__ == "__main__":
    main()
