"""MilkyWay tapered handcrafted evaluation (centipawns, side-to-move relative).

Single pass over bitboards for material, piece-square tables, phase and
mobility, then pawn structure, rook activity, king safety and mop-up. No
legal-move generation here so leaf evaluation stays fast.
"""

from __future__ import annotations

import chess

from constants import (
    MAX_PHASE,
    MW_0_2_EVAL,
    PHASE_WEIGHT_BISHOP,
    PHASE_WEIGHT_KNIGHT,
    PHASE_WEIGHT_QUEEN,
    PHASE_WEIGHT_ROOK,
    EvalParameters,
)

# Active parameters: defaults to immutable MW-0.2 baseline.
ACTIVE_PARAMS: EvalParameters = MW_0_2_EVAL


def get_active_params() -> EvalParameters:
    """Return the currently active evaluation parameter set."""
    return ACTIVE_PARAMS


def set_active_params(params: EvalParameters) -> None:
    """Set the active evaluation parameters."""
    global ACTIVE_PARAMS
    ACTIVE_PARAMS = params


def reset_active_params() -> None:
    """Reset the active evaluation parameters to MW-0.2 baseline."""
    set_active_params(MW_0_2_EVAL)


# Precomputed white PST square transform (sq ^ 56 flips the rank). Black
# squares index the a8..h1-ordered tables directly, so no table is needed.
_WHITE_PST_SQ: tuple[int, ...] = tuple(sq ^ 56 for sq in range(64))

# Precomputed 64-bit passer masks
_WHITE_PASSER_MASKS: list[int] = [0] * 64
_BLACK_PASSER_MASKS: list[int] = [0] * 64
for _sq in range(64):
    _f = _sq & 7
    _r = _sq >> 3
    _w_mask = 0
    _b_mask = 0
    for _df in (-1, 0, 1):
        _nf = _f + _df
        if 0 <= _nf < 8:
            for _nr in range(_r + 1, 8):
                _w_mask |= 1 << ((_nr << 3) | _nf)
            for _nr in range(0, _r):
                _b_mask |= 1 << ((_nr << 3) | _nf)
    _WHITE_PASSER_MASKS[_sq] = _w_mask
    _BLACK_PASSER_MASKS[_sq] = _b_mask

_WHITE_PASSER_MASK_TUPLE: tuple[int, ...] = tuple(_WHITE_PASSER_MASKS)
_BLACK_PASSER_MASK_TUPLE: tuple[int, ...] = tuple(_BLACK_PASSER_MASKS)


def _pawn_structure(
    board: chess.Board,
    color: chess.Color,
    own_pawns: list[int],
    enemy_pawns_mask: int,
    file_counts: list[int],
    p: EvalParameters,
) -> tuple[int, int, list[int]]:
    mg = 0
    eg = 0
    passers: list[int] = []
    passer_masks = _WHITE_PASSER_MASK_TUPLE if color == chess.WHITE else _BLACK_PASSER_MASK_TUPLE
    doubled_mg = p.doubled_pawn_mg
    doubled_eg = p.doubled_pawn_eg
    isolated_mg = p.isolated_pawn_mg
    isolated_eg = p.isolated_pawn_eg
    connected_mg = p.connected_pawn_mg
    connected_eg = p.connected_pawn_eg
    backward_mg = p.backward_pawn_mg // 2
    backward_eg = p.backward_pawn_eg // 2
    passed_mg = p.passed_pawn_mg
    passed_eg = p.passed_pawn_eg
    prot_mg = p.protected_passer_mg
    prot_eg = p.protected_passer_eg

    for sq in own_pawns:
        file = sq & 7
        rank = sq >> 3
        # Doubled: another own pawn on the same file.
        if file_counts[file] > 1:
            mg += doubled_mg
            eg += doubled_eg
        # Isolated: no own pawn on neighbouring files.
        left = file_counts[file - 1] if file > 0 else 0
        right = file_counts[file + 1] if file < 7 else 0
        if left == 0 and right == 0:
            mg += isolated_mg
            eg += isolated_eg
        else:
            # Connected: own pawn beside/behind on a neighbouring file.
            connected = False
            for nfile in (file - 1, file + 1):
                if 0 <= nfile < 8 and file_counts[nfile] > 0:
                    connected = True
                    break
            if connected and not (left == 0 and right == 0):
                mg += connected_mg
                eg += connected_eg

        # Backward
        if left == 0 and right == 0:
            pass
        else:
            behind_rank_ok = False
            for nfile in (file - 1, file + 1):
                if 0 <= nfile < 8:
                    for osq in own_pawns:
                        if (osq & 7) == nfile:
                            orank = osq >> 3
                            if color == chess.WHITE and orank < rank:
                                behind_rank_ok = True
                            if color == chess.BLACK and orank > rank:
                                behind_rank_ok = True
            if not behind_rank_ok:
                mg += backward_mg
                eg += backward_eg

        # Passed pawns via precomputed mask
        if (enemy_pawns_mask & passer_masks[sq]) == 0:
            passers.append(sq)
            adv = rank if color == chess.WHITE else 7 - rank
            adv = max(0, min(7, adv))
            mg += passed_mg[adv]
            eg += passed_eg[adv]
            if board.is_attacked_by(color, sq):
                mg += prot_mg
                eg += prot_eg
    return mg, eg, passers


def _rook_terms(
    color: chess.Color,
    rook_sqs: list[int],
    own_pawn_files: list[int],
    enemy_pawn_files: list[int],
    passers: list[int],
    p: EvalParameters,
) -> tuple[int, int]:
    mg = 0
    eg = 0
    open_mg = p.rook_open_file_mg
    open_eg = p.rook_open_file_eg
    semi_mg = p.rook_semi_open_mg
    semi_eg = p.rook_semi_open_eg
    seventh_mg = p.rook_seventh_mg
    seventh_eg = p.rook_seventh_eg
    conn_mg = p.rook_connected_mg
    behind_mg = p.rook_behind_passer_mg
    behind_eg = p.rook_behind_passer_eg

    for sq in rook_sqs:
        file = sq & 7
        rank = sq >> 3
        own = own_pawn_files[file] > 0
        enemy = enemy_pawn_files[file] > 0
        if not own and not enemy:
            mg += open_mg
            eg += open_eg
        elif not own and enemy:
            mg += semi_mg
            eg += semi_eg
        if (color == chess.WHITE and rank == 6) or (color == chess.BLACK and rank == 1):
            mg += seventh_mg
            eg += seventh_eg
        for other in rook_sqs:
            if other != sq and ((other >> 3) == rank or (other & 7) == file):
                mg += conn_mg
                break
        for psq in passers:
            if (psq & 7) == file:
                prank = psq >> 3
                if color == chess.WHITE and rank < prank:
                    mg += behind_mg
                    eg += behind_eg
                    break
                if color == chess.BLACK and rank > prank:
                    mg += behind_mg
                    eg += behind_eg
                    break
    return mg, eg


def _king_safety(
    board: chess.Board,
    color: chess.Color,
    king_sq: int | None,
    own_pawns_mask: int,
    own_pawn_files: list[int],
    enemy_queens_mask: int,
    p: EvalParameters,
) -> int:
    if king_sq is None:
        return 0
    enemy = not color
    score = 0
    kfile = king_sq & 7
    krank = king_sq >> 3
    # Pawn shield
    shield_ranks: list[int] = []
    if color == chess.WHITE:
        if krank <= 1:
            shield_ranks = [krank + 1, krank + 2]
    elif krank >= 6:
        shield_ranks = [krank - 1, krank - 2]
    if shield_ranks:
        for dfile in (-1, 0, 1):
            f = kfile + dfile
            if 0 <= f < 8:
                shielded = False
                for r in shield_ranks:
                    psq = (r << 3) | f
                    if (own_pawns_mask & (1 << psq)) != 0:
                        shielded = True
                        break
                if not shielded:
                    score += p.king_shield_missing
    # Open files near the king
    home = krank <= 1 if color == chess.WHITE else krank >= 6
    if home:
        for dfile in (-1, 0, 1):
            f = kfile + dfile
            if 0 <= f < 8 and own_pawn_files[f] == 0:
                score += p.king_open_file_near // 2
    # Enemy attacks near the king
    if p.king_safety_variant == "A":
        attacks = 0
        for dfile in (-1, 0, 1):
            for drank in (-1, 0, 1):
                f = kfile + dfile
                r = krank + drank
                if 0 <= f < 8 and 0 <= r < 8 and board.is_attacked_by(enemy, (r << 3) | f):
                    attacks += 1
        score += p.king_attack_unit * attacks
    # Enemy queen proximity
    if enemy_queens_mask:
        q_bb = enemy_queens_mask
        min_qdist = 999
        while q_bb:
            q = (q_bb & -q_bb).bit_length() - 1
            q_bb ^= q_bb & -q_bb
            d = abs((q & 7) - kfile) + abs((q >> 3) - krank)
            if d < min_qdist:
                min_qdist = d
        if min_qdist <= 3:
            score += p.king_attack_unit * (4 - min_qdist)
    return max(score, p.king_max_safety * 2)


def _mop_up(board: chess.Board, white_relative: int, p: EvalParameters) -> int:
    """Encourage efficient conversion when clearly winning."""
    if abs(white_relative) < p.mop_threshold:
        return 0
    try:
        wk = board.king(chess.WHITE)
        bk = board.king(chess.BLACK)
    except ValueError:
        return 0
    if wk is None or bk is None:
        return 0
    winning_white = white_relative > 0
    loser_king = bk if winning_white else wk
    winner_king = wk if winning_white else bk
    lfile = loser_king & 7
    lrank = loser_king >> 3
    edge = min(lfile, 7 - lfile) + min(lrank, 7 - lrank)
    proximity = abs((winner_king & 7) - lfile) + abs((winner_king >> 3) - lrank)
    bonus = (6 - edge) * p.mop_edge_weight + (14 - proximity) * p.mop_proximity_weight
    return bonus if winning_white else -bonus


def evaluate_white_relative(board: chess.Board, params: EvalParameters | None = None) -> int:
    """White-relative static evaluation in centipawns (no mate scores)."""
    p = params if params is not None else ACTIVE_PARAMS
    mg = 0
    eg = 0
    phase = 0

    pawn_v_mg = p.pawn_value_mg
    pawn_v_eg = p.pawn_value_eg
    knight_v_mg = p.knight_value_mg
    knight_v_eg = p.knight_value_eg
    bishop_v_mg = p.bishop_value_mg
    bishop_v_eg = p.bishop_value_eg
    rook_v_mg = p.rook_value_mg
    rook_v_eg = p.rook_value_eg
    queen_v_mg = p.queen_value_mg
    queen_v_eg = p.queen_value_eg

    pawn_mg_pst = p.pawn_mg_pst
    pawn_eg_pst = p.pawn_eg_pst
    knight_pst = p.knight_pst
    bishop_pst = p.bishop_pst
    rook_pst = p.rook_pst
    queen_pst = p.queen_pst
    king_mg_pst = p.king_mg_pst
    king_eg_pst = p.king_eg_pst

    mob_n = p.mobility_knight
    mob_b = p.mobility_bishop
    mob_r = p.mobility_rook
    mob_q = p.mobility_queen

    # Bitboards directly
    w_pawns_mask = board.pieces_mask(chess.PAWN, chess.WHITE)
    b_pawns_mask = board.pieces_mask(chess.PAWN, chess.BLACK)
    w_knights_mask = board.pieces_mask(chess.KNIGHT, chess.WHITE)
    b_knights_mask = board.pieces_mask(chess.KNIGHT, chess.BLACK)
    w_bishops_mask = board.pieces_mask(chess.BISHOP, chess.WHITE)
    b_bishops_mask = board.pieces_mask(chess.BISHOP, chess.BLACK)
    w_rooks_mask = board.pieces_mask(chess.ROOK, chess.WHITE)
    b_rooks_mask = board.pieces_mask(chess.ROOK, chess.BLACK)
    w_queens_mask = board.pieces_mask(chess.QUEEN, chess.WHITE)
    b_queens_mask = board.pieces_mask(chess.QUEEN, chess.BLACK)
    w_king_mask = board.pieces_mask(chess.KING, chess.WHITE)
    b_king_mask = board.pieces_mask(chess.KING, chess.BLACK)

    # Collections
    w_pawns: list[int] = []
    b_pawns: list[int] = []
    w_rooks: list[int] = []
    b_rooks: list[int] = []
    w_pawn_files = [0] * 8
    b_pawn_files = [0] * 8

    # White pawns
    bb = w_pawns_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        w_pawns.append(sq)
        idx = _WHITE_PST_SQ[sq]
        mg += pawn_v_mg + pawn_mg_pst[idx]
        eg += pawn_v_eg + pawn_eg_pst[idx]
        w_pawn_files[sq & 7] += 1

    # Black pawns
    bb = b_pawns_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        b_pawns.append(sq)
        idx = sq
        mg -= pawn_v_mg + pawn_mg_pst[idx]
        eg -= pawn_v_eg + pawn_eg_pst[idx]
        b_pawn_files[sq & 7] += 1

    # White knights
    w_mob = 0
    bb = w_knights_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = _WHITE_PST_SQ[sq]
        mg += knight_v_mg + knight_pst[idx]
        eg += knight_v_eg + knight_pst[idx]
        phase += PHASE_WEIGHT_KNIGHT
        w_mob += mob_n * board.attacks_mask(sq).bit_count()

    # Black knights
    b_mob = 0
    bb = b_knights_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = sq
        mg -= knight_v_mg + knight_pst[idx]
        eg -= knight_v_eg + knight_pst[idx]
        phase += PHASE_WEIGHT_KNIGHT
        b_mob += mob_n * board.attacks_mask(sq).bit_count()

    # White bishops
    w_bishops = 0
    bb = w_bishops_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        w_bishops += 1
        idx = _WHITE_PST_SQ[sq]
        mg += bishop_v_mg + bishop_pst[idx]
        eg += bishop_v_eg + bishop_pst[idx]
        phase += PHASE_WEIGHT_BISHOP
        w_mob += mob_b * board.attacks_mask(sq).bit_count()

    # Black bishops
    b_bishops = 0
    bb = b_bishops_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        b_bishops += 1
        idx = sq
        mg -= bishop_v_mg + bishop_pst[idx]
        eg -= bishop_v_eg + bishop_pst[idx]
        phase += PHASE_WEIGHT_BISHOP
        b_mob += mob_b * board.attacks_mask(sq).bit_count()

    # White rooks
    bb = w_rooks_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        w_rooks.append(sq)
        idx = _WHITE_PST_SQ[sq]
        mg += rook_v_mg + rook_pst[idx]
        eg += rook_v_eg + rook_pst[idx]
        phase += PHASE_WEIGHT_ROOK
        w_mob += mob_r * board.attacks_mask(sq).bit_count()

    # Black rooks
    bb = b_rooks_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        b_rooks.append(sq)
        idx = sq
        mg -= rook_v_mg + rook_pst[idx]
        eg -= rook_v_eg + rook_pst[idx]
        phase += PHASE_WEIGHT_ROOK
        b_mob += mob_r * board.attacks_mask(sq).bit_count()

    # White queens
    bb = w_queens_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = _WHITE_PST_SQ[sq]
        mg += queen_v_mg + queen_pst[idx]
        eg += queen_v_eg + queen_pst[idx]
        phase += PHASE_WEIGHT_QUEEN
        w_mob += mob_q * board.attacks_mask(sq).bit_count()

    # Black queens
    bb = b_queens_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = sq
        mg -= queen_v_mg + queen_pst[idx]
        eg -= queen_v_eg + queen_pst[idx]
        phase += PHASE_WEIGHT_QUEEN
        b_mob += mob_q * board.attacks_mask(sq).bit_count()

    # Kings
    if w_king_mask:
        w_king_sq = (w_king_mask & -w_king_mask).bit_length() - 1
        idx = _WHITE_PST_SQ[w_king_sq]
        mg += king_mg_pst[idx]
        eg += king_eg_pst[idx]
    else:
        w_king_sq = None

    if b_king_mask:
        b_king_sq = (b_king_mask & -b_king_mask).bit_length() - 1
        idx = b_king_sq
        mg -= king_mg_pst[idx]
        eg -= king_eg_pst[idx]
    else:
        b_king_sq = None

    phase = max(0, min(MAX_PHASE, phase))
    mg_weight = phase / MAX_PHASE
    eg_weight = 1.0 - mg_weight

    # Bishop pair
    if w_bishops >= 2:
        mg += p.bishop_pair_mg
        eg += p.bishop_pair_eg
    if b_bishops >= 2:
        mg -= p.bishop_pair_mg
        eg -= p.bishop_pair_eg

    # Pawn structure
    wpmg, wpeg, w_passers = _pawn_structure(
        board, chess.WHITE, w_pawns, b_pawns_mask, w_pawn_files, p
    )
    bpmg, bpeg, b_passers = _pawn_structure(
        board, chess.BLACK, b_pawns, w_pawns_mask, b_pawn_files, p
    )
    mg += wpmg - bpmg
    eg += wpeg - bpeg

    # Rook terms
    wrmg, wreg = _rook_terms(chess.WHITE, w_rooks, w_pawn_files, b_pawn_files, w_passers, p)
    brmg, breg = _rook_terms(chess.BLACK, b_rooks, b_pawn_files, w_pawn_files, b_passers, p)
    mg += wrmg - brmg
    eg += wreg - breg

    # Mobility
    mob = w_mob - b_mob
    mg += int(mob * 0.7)
    eg += int(mob * 0.3)

    # King safety
    wks = _king_safety(board, chess.WHITE, w_king_sq, w_pawns_mask, w_pawn_files, b_queens_mask, p)
    bks = _king_safety(board, chess.BLACK, b_king_sq, b_pawns_mask, b_pawn_files, w_queens_mask, p)
    mg += wks - bks
    eg += int((wks - bks) * 0.2)

    tapered = int(mg * mg_weight + eg * eg_weight)
    tapered += _mop_up(board, tapered, p)
    return tapered


def evaluate(board: chess.Board, params: EvalParameters | None = None) -> int:
    """Side-to-move-relative evaluation in centipawns."""
    white_rel = evaluate_white_relative(board, params)
    return white_rel if board.turn == chess.WHITE else -white_rel
