"""MilkyWay competition entrypoint. The platform imports this file."""

from __future__ import annotations

import chess

from engine import get_engine_move


def get_move(fen: str, time_left_ms: int) -> str:
    """Return a legal move in UCI notation.

    fen           the position to move in; your colour is the side to move
    time_left_ms  your clock before this move, in milliseconds
    returns       "e2e4", or "e7e8q" for a promotion
    """
    # Validate the FEN once so a malformed request never crashes the process;
    # fall back to a safe default only if the position itself is broken.
    try:
        board = chess.Board(fen)
    except ValueError:
        return "0000"
    if not list(board.legal_moves):
        return "0000"
    move_uci = get_engine_move(fen, time_left_ms)
    # Final safety net: never return an illegal move.
    try:
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            return move_uci
    except chess.InvalidMoveError:
        pass
    return sorted(m.uci() for m in board.legal_moves)[0]
