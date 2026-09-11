"""Move ordering: TT move, promotions, MVV-LVA captures, killers, history.

silky-snow: the per-move scoring loop is the hottest Python code in the
searcher (200k+ calls per deep search), so it has been inlined. The rewrite is
order-for-order identical to the original but avoids:
  * one Python function call per move (score_move)
  * a lambda sort key (replaced by precomputed negation + plain tuple sort)
  * board.is_capture() / piece_type_at() attribute lookups (bitboards instead)
"""

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

_BB = chess.BB_SQUARES


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
    """Return moves sorted best-first (deterministic tie-break by move encoding).

    Scores are stored negated so a plain tuple sort (no key lambda) yields
    descending score with ascending tie-break. The tie-break is unique per
    move, so comparison never reaches the non-comparable Move object.
    """
    hist = history[1 if board.turn else 0]
    them = board.occupied_co[not board.turn]
    pawns = board.pawns
    knights = board.knights
    bishops = board.bishops
    rooks = board.rooks
    queens = board.queens
    ep_sq = board.ep_square
    k0 = killers[0]
    k1 = killers[1]
    bb = _BB

    scored: list[tuple[int, int, chess.Move]] = []
    ap = scored.append
    for move in moves:
        frm = move.from_square
        to = move.to_square
        promo = move.promotion
        # Unique per move: comparison never falls through to the Move object.
        tie = (frm << 6) | to | ((promo or 0) << 12)

        if tt_move is not None and move == tt_move:
            ap((-100000, tie, move))
            continue

        if promo is not None:
            # Promotions are rare; the slow path keeps exact parity.
            mvv = capture_mvv_lva(board, move)
            s = PROMOTION_BONUS + _PIECE_VALUE_MAP.get(promo, 0) + max(0, mvv // 8)
            ap((-s, tie, move))
            continue

        m_to = bb[to]
        if m_to & them:
            # Capture: MVV-LVA straight off the bitboards.
            if m_to & pawns:
                vv = PAWN_VALUE
            elif m_to & knights:
                vv = KNIGHT_VALUE
            elif m_to & bishops:
                vv = BISHOP_VALUE
            elif m_to & rooks:
                vv = ROOK_VALUE
            else:
                vv = QUEEN_VALUE
            m_frm = bb[frm]
            if m_frm & pawns:
                av = PAWN_VALUE
            elif m_frm & knights:
                av = KNIGHT_VALUE
            elif m_frm & bishops:
                av = BISHOP_VALUE
            elif m_frm & rooks:
                av = ROOK_VALUE
            elif m_frm & queens:
                av = QUEEN_VALUE
            else:
                av = 0
            ap((-(GOOD_CAPTURE_BASE + vv * 16 - av), tie, move))
            continue

        # En passant: the victim is a pawn but the target square is empty, so
        # the bitboard test above cannot see it. ep_square is usually None,
        # which short-circuits this for essentially every quiet move.
        if ep_sq is not None and to == ep_sq and (bb[frm] & pawns) and abs(to - frm) in (7, 9):
            ap((-(GOOD_CAPTURE_BASE + PAWN_VALUE * 16 - PAWN_VALUE), tie, move))
            continue

        if move == k0:
            ap((-(KILLER_BONUS + 100), tie, move))
            continue
        if move == k1:
            ap((-KILLER_BONUS, tie, move))
            continue

        hs = hist[frm][to]
        ap((-(hs if hs < HISTORY_MAX_BONUS else HISTORY_MAX_BONUS), tie, move))

    scored.sort()
    return [m for _, _, m in scored]


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
    # Logits have an arbitrary common offset. Center quiet moves before
    # clipping so the best predictions do not collapse into a +5 tie.
    quiet_peak = max((policy_scores.get(m, -50.0) for m in moves
                      if m.promotion is None and not board.is_capture(m)), default=0.0)
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
            gives_check = board.gives_check(move)
            check_s = float(CHECK_BONUS) if gives_check else 0.0
            h = history[stm][move.from_square][move.to_square]
            classical_h = float(min(h, HISTORY_MAX_BONUS))
            p_score = policy_scores.get(move, -50.0) if policy_scores else 0.0
            clamped_p = max(-5.0, min(5.0, p_score - quiet_peak))
            p_bonus = clamped_p * 150.0
            quiet_s = check_s + classical_h + p_bonus
            s = min(float(GOOD_CAPTURE_BASE - 100), quiet_s)

        tie = (move.from_square << 6) | move.to_square | ((move.promotion or 0) << 12)
        scored.append((s, tie, move))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [move for _, _, move in scored]
