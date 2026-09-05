"""Move ordering: TT move, promotions, MVV-LVA captures, killers, history."""

from __future__ import annotations

import chess

from constants import BISHOP_VALUE, KNIGHT_VALUE, PAWN_VALUE, QUEEN_VALUE, ROOK_VALUE

_PIECE_VALUE_MAP: dict[chess.PieceType, int] = {
    chess.PAWN: PAWN_VALUE,
    chess.KNIGHT: KNIGHT_VALUE,
    chess.BISHOP: BISHOP_VALUE,
    chess.ROOK: ROOK_VALUE,
    chess.QUEEN: QUEEN_VALUE,
    chess.KING: 0,
}

# Ordering bonuses (larger = searched earlier). TT move is handled by forcing
# it to the front rather than by score magnitude.
PROMOTION_BONUS: int = 9000
GOOD_CAPTURE_BASE: int = 7000
KILLER_BONUS: int = 5000
CHECK_BONUS: int = 3000
HISTORY_MAX_BONUS: int = 2500


def capture_mvv_lva(board: chess.Board, move: chess.Move) -> int:
    """Most Valuable Victim / Least Valuable Attacker score."""
    victim: chess.PieceType | None = None
    if board.is_en_passant(move):
        victim = chess.PAWN
    else:
        target = board.piece_at(move.to_square)
        if target is not None:
            victim = target.piece_type
    if victim is None:
        return 0
    attacker = board.piece_at(move.from_square)
    attacker_value = _PIECE_VALUE_MAP[attacker.piece_type] if attacker is not None else 0
    victim_value = _PIECE_VALUE_MAP[victim]
    return victim_value * 16 - attacker_value


def is_tactical(board: chess.Board, move: chess.Move) -> bool:
    return board.is_capture(move) or move.promotion is not None


def score_move(
    board: chess.Board,
    move: chess.Move,
    tt_move: chess.Move | None,
    killers: tuple[chess.Move | None, chess.Move | None],
    history_score: int,
    gives_check: bool,
) -> int:
    if tt_move is not None and move == tt_move:
        return 100000
    if move.promotion is not None:
        promo = move.promotion
        promo_value = _PIECE_VALUE_MAP.get(promo, 0)
        # Queen promotions far above underpromotions; captures add MVV-LVA.
        return PROMOTION_BONUS + promo_value + max(0, capture_mvv_lva(board, move) // 8)
    if board.is_capture(move):
        mvv = capture_mvv_lva(board, move)
        # Obviously losing captures (e.g. pawn takes defended queen... actually
        # winning) — keep simple: most captures are good; SEE comes later.
        return GOOD_CAPTURE_BASE + mvv
    if killers[0] is not None and move == killers[0]:
        return KILLER_BONUS + 100
    if killers[1] is not None and move == killers[1]:
        return KILLER_BONUS
    if gives_check:
        return CHECK_BONUS + min(history_score, HISTORY_MAX_BONUS)
    return min(history_score, HISTORY_MAX_BONUS)


def order_moves(
    board: chess.Board,
    moves: list[chess.Move],
    tt_move: chess.Move | None,
    killers: tuple[chess.Move | None, chess.Move | None],
    history: list[list[list[int]]],
) -> list[chess.Move]:
    """Return moves sorted best-first (deterministic tie-break by UCI)."""
    stm = 1 if board.turn == chess.WHITE else 0
    scored: list[tuple[int, str, chess.Move]] = []
    for move in moves:
        h = history[stm][move.from_square][move.to_square]
        # Check detection needs push; do it sparingly — only for quiet moves
        # that could earn the check bonus. Captures/promotions/TT already rank.
        gives_check = False
        if (tt_move is None or move != tt_move) and (
            not board.is_capture(move) and move.promotion is None
        ):
            board.push(move)
            gives_check = board.is_check()
            board.pop()
        s = score_move(board, move, tt_move, killers, h, gives_check)
        scored.append((s, move.uci(), move))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [move for _, _, move in scored]
