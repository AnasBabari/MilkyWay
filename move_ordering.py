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
    if board.is_en_passant(move):
        victim = chess.PAWN
    else:
        target = board.piece_type_at(move.to_square)
        if target is None:
            return 0
        victim = target
    attacker = board.piece_type_at(move.from_square)
    attacker_value = _PIECE_VALUE_MAP[attacker] if attacker is not None else 0
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
    """Return moves sorted best-first (deterministic tie-break by integer move encoding)."""
    stm = 1 if board.turn == chess.WHITE else 0
    scored: list[tuple[int, int, chess.Move]] = []
    for move in moves:
        h = history[stm][move.from_square][move.to_square]
        # Quiet moves do not probe check with push/pop (hotspot eliminated).
        s = score_move(board, move, tt_move, killers, h, False)
        # Deterministic integer tie-break: avoid string allocation overhead
        tie = (move.from_square << 6) | move.to_square | ((move.promotion or 0) << 12)
        scored.append((s, tie, move))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [move for _, _, move in scored]


def order_root_moves(
    board: chess.Board,
    moves: list[chess.Move],
    tt_move: chess.Move | None,
    policy_scores: dict[chess.Move, float],
    history: list[list[list[int]]],
) -> list[chess.Move]:
    """Order root moves using TT move, promotions, captures, and neural policy scores.

    TT move is always prioritized first. Promotions and captures follow classical MVV-LVA.
    Quiet moves are ordered primarily by neural policy logits, blended with classical history,
    capped strictly below good captures so quiet moves never jump ahead of tactical captures.
    """
    stm = 1 if board.turn == chess.WHITE else 0
    scored: list[tuple[float, int, chess.Move]] = []
    for move in moves:
        if tt_move is not None and move == tt_move:
            s = 100000.0
        elif move.promotion is not None:
            promo = move.promotion
            promo_value = _PIECE_VALUE_MAP.get(promo, 0)
            s = float(PROMOTION_BONUS + promo_value + max(0, capture_mvv_lva(board, move) // 8))
        elif board.is_capture(move):
            mvv = capture_mvv_lva(board, move)
            s = float(GOOD_CAPTURE_BASE + mvv)
        else:
            h = history[stm][move.from_square][move.to_square]
            classical_h = float(min(h, HISTORY_MAX_BONUS))
            p_score = policy_scores.get(move, -50.0) if policy_scores else 0.0
            quiet_s = classical_h + p_score * 300.0
            s = min(float(GOOD_CAPTURE_BASE - 100), quiet_s)

        tie = (move.from_square << 6) | move.to_square | ((move.promotion or 0) << 12)
        scored.append((s, tie, move))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [move for _, _, move in scored]

