"""Shared tactical/edge-case positions for MilkyWay tests."""

from __future__ import annotations

START_FEN: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# White to move, Qxf7# (Scholar's mate finish).
MATE_IN_1_FEN: str = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 4 3"
MATE_IN_1_MOVE: str = "f3f7"

# Black to move and mated on the move unless they block/capture correctly;
# white queen + bishop battery. Engine (black) must not walk into mate.
AVOID_MATE_FEN: str = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR b KQkq - 4 3"

# White to move, hanging black queen on d5: Qxd5 wins material.
HANGING_QUEEN_FEN: str = "rnb1kbnr/ppp1pppp/8/3q4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"

# Promotion: white pawn on g7 must promote (g7g8q wins).
PROMOTION_FEN: str = "7k/6P1/8/8/8/8/5PPP/6K1 w - - 0 1"

# En passant available: white pawn e5, black just played d7d5.
EN_PASSANT_FEN: str = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 1"

# Kingside castling available for white.
CASTLING_FEN: str = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"

# Stalemate for the side to move (black, no legal moves, not in check).
STALEMATE_FEN: str = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
