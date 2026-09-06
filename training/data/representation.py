"""MilkyWay M17 — Chess board and move representation.

Version: m17_18x8x8_v1
Planes:
  0..5:   White P, N, B, R, Q, K
  6..11:  Black P, N, B, R, Q, K
  12:     Side to move (1=White, 0=Black)
  13:     White kingside castling
  14:     White queenside castling
  15:     Black kingside castling
  16:     Black queenside castling
  17:     En-passant target square (1 at target square, 0 elsewhere)

Move Vocabulary:
  Deterministic vocabulary of 1968 geometric moves covering all standard UCI moves
  including promotions (q, r, b, n), castling, captures, and en passant.
"""

from __future__ import annotations

import chess
import numpy as np

from root_policy import (
    BOARD_SHAPE,
    MOVE_VOCABULARY_SIZE,
    NUM_PLANES,
    PIECE_TO_PLANE,
    PLANE_CASTLE_BLACK_KINGSIDE,
    PLANE_CASTLE_BLACK_QUEENSIDE,
    PLANE_CASTLE_WHITE_KINGSIDE,
    PLANE_CASTLE_WHITE_QUEENSIDE,
    PLANE_EN_PASSANT,
    PLANE_SIDE_TO_MOVE,
    PLANE_TO_PIECE,
    VOCAB_INDEX_TO_UCI,
    VOCAB_UCI_TO_INDEX,
    board_to_tensor,
    fen_to_tensor,
    index_to_move,
    index_to_uci,
    move_to_index,
)

REPRESENTATION_VERSION: str = "m17_18x8x8_v1"

__all__ = (
    "BOARD_SHAPE",
    "MOVE_VOCABULARY_SIZE",
    "NUM_PLANES",
    "PIECE_TO_PLANE",
    "PLANE_CASTLE_BLACK_KINGSIDE",
    "PLANE_CASTLE_BLACK_QUEENSIDE",
    "PLANE_CASTLE_WHITE_KINGSIDE",
    "PLANE_CASTLE_WHITE_QUEENSIDE",
    "PLANE_EN_PASSANT",
    "PLANE_SIDE_TO_MOVE",
    "PLANE_TO_PIECE",
    "REPRESENTATION_VERSION",
    "VOCAB_INDEX_TO_UCI",
    "VOCAB_UCI_TO_INDEX",
    "board_to_tensor",
    "fen_to_tensor",
    "index_to_move",
    "index_to_uci",
    "move_to_index",
    "tensor_to_board",
)


def tensor_to_board(tensor: np.ndarray) -> chess.Board:
    """Reconstruct a chess.Board from uint8 ndarray of shape (18, 8, 8)."""
    if tensor.shape != BOARD_SHAPE:
        raise ValueError(f"Expected shape {BOARD_SHAPE}, got {tensor.shape}")

    board = chess.Board(fen=None)

    for plane_idx in range(12):
        piece_type, color = PLANE_TO_PIECE[plane_idx]
        coords = np.argwhere(tensor[plane_idx] == 1)
        for r, f in coords:
            sq = int(r * 8 + f)
            board.set_piece_at(sq, chess.Piece(piece_type, color))

    board.turn = chess.WHITE if tensor[PLANE_SIDE_TO_MOVE, 0, 0] == 1 else chess.BLACK

    castling_mask = 0
    if tensor[PLANE_CASTLE_WHITE_KINGSIDE, 0, 0] == 1:
        castling_mask |= chess.BB_H1
    if tensor[PLANE_CASTLE_WHITE_QUEENSIDE, 0, 0] == 1:
        castling_mask |= chess.BB_A1
    if tensor[PLANE_CASTLE_BLACK_KINGSIDE, 0, 0] == 1:
        castling_mask |= chess.BB_H8
    if tensor[PLANE_CASTLE_BLACK_QUEENSIDE, 0, 0] == 1:
        castling_mask |= chess.BB_A8
    board.castling_rights = castling_mask

    ep_coords = np.argwhere(tensor[PLANE_EN_PASSANT] == 1)
    if len(ep_coords) > 0:
        board.ep_square = int(ep_coords[0][0] * 8 + ep_coords[0][1])
    else:
        board.ep_square = None

    return board
