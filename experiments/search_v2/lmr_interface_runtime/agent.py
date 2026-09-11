"""Experimental original compiled MilkyWay search with the team's learned value."""
from __future__ import annotations

import time

import chess
from core import encode_board
from reduced_search import position_key, search

from time_manager import allocate_time

_board: chess.Board | None = None
_keys: list[int] = []
_last_search: dict = {}


def _key(board: chess.Board) -> int:
    array, side, rights, ep = encode_board(board)
    return int(position_key(array, side, rights, ep))


def _synchronize(incoming: chess.Board) -> None:
    """Extend history only when the observed opponent move is legally identified."""
    global _board, _keys
    if _board is not None:
        wanted = incoming.fen()
        for move in list(_board.legal_moves):
            _board.push(move)
            if _board.fen() == wanted:
                _keys.append(_key(_board))
                return
            _board.pop()
    _board = incoming.copy()
    _keys = [_key(_board)]


def get_move(fen: str, time_left_ms: int) -> str:
    global _last_search
    started = time.perf_counter()
    incoming = chess.Board(fen)
    legal = list(incoming.legal_moves)
    if not legal:
        return "0000"
    _synchronize(incoming)
    assert _board is not None
    best = min(legal, key=lambda m: m.uci())
    budget = allocate_time(time_left_ms, len(legal), increment_ms=500)
    overhead = time.perf_counter() - started
    # Retain an IPC cushion beyond the existing allocator's reserve.
    hard = max(0.0, min(budget.hard_ms / 1000.0,
                        time_left_ms / 1000.0 - 0.025) - overhead)
    soft = max(0.0, min(hard, budget.soft_ms / 1000.0 - overhead))
    if len(legal) > 1 and hard > 0.005:
        _last_search = search(_board, seconds=hard, soft_seconds=soft,
                              max_depth=40, coefficient=0.25, prior_keys=_keys[:-1])
        proposed = chess.Move.from_uci(_last_search["move"])
        if proposed in legal:
            best = proposed
    else:
        _last_search = {"depth": 0, "move": best.uci(), "elapsed_s": 0.0}
    _board.push(best)
    _keys.append(_key(_board))
    return best.uci()


# Compile recursive search and helpers during import, outside the game clock.
search(chess.Board(), seconds=0.0, soft_seconds=0.0, max_depth=1,
       coefficient=0.25, prior_keys=[])
