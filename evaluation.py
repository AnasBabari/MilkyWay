"""MilkyWay tapered handcrafted evaluation (centipawns, side-to-move relative).

Single pass over bitboards for material, piece-square tables, phase and
mobility, then pawn structure, rook activity, king safety and mop-up. No
legal-move generation here so leaf evaluation stays fast.
"""

from __future__ import annotations

import chess

from constants import (
    BACKWARD_PAWN_EG,
    BACKWARD_PAWN_MG,
    BISHOP_PAIR_EG,
    BISHOP_PAIR_MG,
    BISHOP_PST,
    BISHOP_VALUE,
    CONNECTED_PAWN_EG,
    CONNECTED_PAWN_MG,
    DOUBLED_PAWN_EG,
    DOUBLED_PAWN_MG,
    ISOLATED_PAWN_EG,
    ISOLATED_PAWN_MG,
    KING_ATTACK_UNIT,
    KING_EG,
    KING_MAX_SAFETY,
    KING_MG,
    KING_OPEN_FILE_NEAR,
    KING_SHIELD_MISSING,
    KNIGHT_PST,
    KNIGHT_VALUE,
    MAX_PHASE,
    MOBILITY_BISHOP,
    MOBILITY_KNIGHT,
    MOBILITY_QUEEN,
    MOBILITY_ROOK,
    MOP_EDGE_WEIGHT,
    MOP_PROXIMITY_WEIGHT,
    MOP_THRESHOLD,
    PASSED_PAWN_EG,
    PASSED_PAWN_MG,
    PAWN_EG,
    PAWN_MG,
    PAWN_VALUE,
    PHASE_WEIGHT_BISHOP,
    PHASE_WEIGHT_KNIGHT,
    PHASE_WEIGHT_QUEEN,
    PHASE_WEIGHT_ROOK,
    PROTECTED_PASSER_EG,
    PROTECTED_PASSER_MG,
    QUEEN_PST,
    QUEEN_VALUE,
    ROOK_BEHIND_PASSER_EG,
    ROOK_BEHIND_PASSER_MG,
    ROOK_CONNECTED_MG,
    ROOK_OPEN_FILE_EG,
    ROOK_OPEN_FILE_MG,
    ROOK_PST,
    ROOK_SEMI_OPEN_EG,
    ROOK_SEMI_OPEN_MG,
    ROOK_SEVENTH_EG,
    ROOK_SEVENTH_MG,
    ROOK_VALUE,
)

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
) -> tuple[int, int, list[int]]:
    mg = 0
    eg = 0
    passers: list[int] = []
    passer_masks = _WHITE_PASSER_MASK_TUPLE if color == chess.WHITE else _BLACK_PASSER_MASK_TUPLE
    for sq in own_pawns:
        file = sq & 7
        rank = sq >> 3
        # Doubled: another own pawn on the same file.
        if file_counts[file] > 1:
            mg += DOUBLED_PAWN_MG
            eg += DOUBLED_PAWN_EG
        # Isolated: no own pawn on neighbouring files.
        left = file_counts[file - 1] if file > 0 else 0
        right = file_counts[file + 1] if file < 7 else 0
        if left == 0 and right == 0:
            mg += ISOLATED_PAWN_MG
            eg += ISOLATED_PAWN_EG
        else:
            # Connected: own pawn beside/behind on a neighbouring file.
            connected = False
            for nfile in (file - 1, file + 1):
                if 0 <= nfile < 8 and file_counts[nfile] > 0:
                    connected = True
                    break
            if connected and not (left == 0 and right == 0):
                mg += CONNECTED_PAWN_MG
                eg += CONNECTED_PAWN_EG

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
                mg += BACKWARD_PAWN_MG // 2
                eg += BACKWARD_PAWN_EG // 2

        # Passed pawns via precomputed mask
        if (enemy_pawns_mask & passer_masks[sq]) == 0:
            passers.append(sq)
            adv = rank if color == chess.WHITE else 7 - rank
            adv = max(0, min(7, adv))
            mg += PASSED_PAWN_MG[adv]
            eg += PASSED_PAWN_EG[adv]
            if board.is_attacked_by(color, sq):
                mg += PROTECTED_PASSER_MG
                eg += PROTECTED_PASSER_EG
    return mg, eg, passers


def _rook_terms(
    color: chess.Color,
    rook_sqs: list[int],
    own_pawn_files: list[int],
    enemy_pawn_files: list[int],
    passers: list[int],
) -> tuple[int, int]:
    mg = 0
    eg = 0
    for sq in rook_sqs:
        file = sq & 7
        rank = sq >> 3
        own = own_pawn_files[file] > 0
        enemy = enemy_pawn_files[file] > 0
        if not own and not enemy:
            mg += ROOK_OPEN_FILE_MG
            eg += ROOK_OPEN_FILE_EG
        elif not own and enemy:
            mg += ROOK_SEMI_OPEN_MG
            eg += ROOK_SEMI_OPEN_EG
        if (color == chess.WHITE and rank == 6) or (color == chess.BLACK and rank == 1):
            mg += ROOK_SEVENTH_MG
            eg += ROOK_SEVENTH_EG
        for other in rook_sqs:
            if other != sq and ((other >> 3) == rank or (other & 7) == file):
                mg += ROOK_CONNECTED_MG
                break
        for psq in passers:
            if (psq & 7) == file:
                prank = psq >> 3
                if color == chess.WHITE and rank < prank:
                    mg += ROOK_BEHIND_PASSER_MG
                    eg += ROOK_BEHIND_PASSER_EG
                    break
                if color == chess.BLACK and rank > prank:
                    mg += ROOK_BEHIND_PASSER_MG
                    eg += ROOK_BEHIND_PASSER_EG
                    break
    return mg, eg


def _king_safety(
    board: chess.Board,
    color: chess.Color,
    king_sq: int | None,
    own_pawns_mask: int,
    own_pawn_files: list[int],
    enemy_queens_mask: int,
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
                    score += KING_SHIELD_MISSING
    # Open files near the king
    home = krank <= 1 if color == chess.WHITE else krank >= 6
    if home:
        for dfile in (-1, 0, 1):
            f = kfile + dfile
            if 0 <= f < 8 and own_pawn_files[f] == 0:
                score += KING_OPEN_FILE_NEAR // 2
    # Enemy attacks near the king
    attacks = 0
    for dfile in (-1, 0, 1):
        for drank in (-1, 0, 1):
            f = kfile + dfile
            r = krank + drank
            if 0 <= f < 8 and 0 <= r < 8 and board.is_attacked_by(enemy, (r << 3) | f):
                attacks += 1
    score += KING_ATTACK_UNIT * attacks
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
            score += KING_ATTACK_UNIT * (4 - min_qdist)
    return max(score, KING_MAX_SAFETY * 2)


def _mop_up(board: chess.Board, white_relative: int) -> int:
    """Encourage efficient conversion when clearly winning."""
    if abs(white_relative) < MOP_THRESHOLD:
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
    bonus = (6 - edge) * MOP_EDGE_WEIGHT + (14 - proximity) * MOP_PROXIMITY_WEIGHT
    return bonus if winning_white else -bonus


def evaluate_white_relative(board: chess.Board) -> int:
    """White-relative static evaluation in centipawns (no mate scores)."""
    mg = 0
    eg = 0
    phase = 0

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
        mg += PAWN_VALUE + PAWN_MG[idx]
        eg += PAWN_VALUE + PAWN_EG[idx]
        w_pawn_files[sq & 7] += 1

    # Black pawns
    bb = b_pawns_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        b_pawns.append(sq)
        idx = sq
        mg -= PAWN_VALUE + PAWN_MG[idx]
        eg -= PAWN_VALUE + PAWN_EG[idx]
        b_pawn_files[sq & 7] += 1

    # White knights
    w_mob = 0
    bb = w_knights_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = _WHITE_PST_SQ[sq]
        mg += KNIGHT_VALUE + KNIGHT_PST[idx]
        eg += KNIGHT_VALUE + KNIGHT_PST[idx]
        phase += PHASE_WEIGHT_KNIGHT
        w_mob += MOBILITY_KNIGHT * board.attacks_mask(sq).bit_count()

    # Black knights
    b_mob = 0
    bb = b_knights_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = sq
        mg -= KNIGHT_VALUE + KNIGHT_PST[idx]
        eg -= KNIGHT_VALUE + KNIGHT_PST[idx]
        phase += PHASE_WEIGHT_KNIGHT
        b_mob += MOBILITY_KNIGHT * board.attacks_mask(sq).bit_count()

    # White bishops
    w_bishops = 0
    bb = w_bishops_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        w_bishops += 1
        idx = _WHITE_PST_SQ[sq]
        mg += BISHOP_VALUE + BISHOP_PST[idx]
        eg += BISHOP_VALUE + BISHOP_PST[idx]
        phase += PHASE_WEIGHT_BISHOP
        w_mob += MOBILITY_BISHOP * board.attacks_mask(sq).bit_count()

    # Black bishops
    b_bishops = 0
    bb = b_bishops_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        b_bishops += 1
        idx = sq
        mg -= BISHOP_VALUE + BISHOP_PST[idx]
        eg -= BISHOP_VALUE + BISHOP_PST[idx]
        phase += PHASE_WEIGHT_BISHOP
        b_mob += MOBILITY_BISHOP * board.attacks_mask(sq).bit_count()

    # White rooks
    bb = w_rooks_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        w_rooks.append(sq)
        idx = _WHITE_PST_SQ[sq]
        mg += ROOK_VALUE + ROOK_PST[idx]
        eg += ROOK_VALUE + ROOK_PST[idx]
        phase += PHASE_WEIGHT_ROOK
        w_mob += MOBILITY_ROOK * board.attacks_mask(sq).bit_count()

    # Black rooks
    bb = b_rooks_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        b_rooks.append(sq)
        idx = sq
        mg -= ROOK_VALUE + ROOK_PST[idx]
        eg -= ROOK_VALUE + ROOK_PST[idx]
        phase += PHASE_WEIGHT_ROOK
        b_mob += MOBILITY_ROOK * board.attacks_mask(sq).bit_count()

    # White queens
    bb = w_queens_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = _WHITE_PST_SQ[sq]
        mg += QUEEN_VALUE + QUEEN_PST[idx]
        eg += QUEEN_VALUE + QUEEN_PST[idx]
        phase += PHASE_WEIGHT_QUEEN
        w_mob += MOBILITY_QUEEN * board.attacks_mask(sq).bit_count()

    # Black queens
    bb = b_queens_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = sq
        mg -= QUEEN_VALUE + QUEEN_PST[idx]
        eg -= QUEEN_VALUE + QUEEN_PST[idx]
        phase += PHASE_WEIGHT_QUEEN
        b_mob += MOBILITY_QUEEN * board.attacks_mask(sq).bit_count()

    # Kings
    if w_king_mask:
        w_king_sq = (w_king_mask & -w_king_mask).bit_length() - 1
        idx = _WHITE_PST_SQ[w_king_sq]
        mg += KING_MG[idx]
        eg += KING_EG[idx]
    else:
        w_king_sq = None

    if b_king_mask:
        b_king_sq = (b_king_mask & -b_king_mask).bit_length() - 1
        idx = b_king_sq
        mg -= KING_MG[idx]
        eg -= KING_EG[idx]
    else:
        b_king_sq = None

    phase = max(0, min(MAX_PHASE, phase))
    mg_weight = phase / MAX_PHASE
    eg_weight = 1.0 - mg_weight

    # Bishop pair
    if w_bishops >= 2:
        mg += BISHOP_PAIR_MG
        eg += BISHOP_PAIR_EG
    if b_bishops >= 2:
        mg -= BISHOP_PAIR_MG
        eg -= BISHOP_PAIR_EG

    # Pawn structure
    wpmg, wpeg, w_passers = _pawn_structure(
        board, chess.WHITE, w_pawns, b_pawns_mask, w_pawn_files
    )
    bpmg, bpeg, b_passers = _pawn_structure(
        board, chess.BLACK, b_pawns, w_pawns_mask, b_pawn_files
    )
    mg += wpmg - bpmg
    eg += wpeg - bpeg

    # Rook terms
    wrmg, wreg = _rook_terms(chess.WHITE, w_rooks, w_pawn_files, b_pawn_files, w_passers)
    brmg, breg = _rook_terms(chess.BLACK, b_rooks, b_pawn_files, w_pawn_files, b_passers)
    mg += wrmg - brmg
    eg += wreg - breg

    # Mobility
    mob = w_mob - b_mob
    mg += int(mob * 0.7)
    eg += int(mob * 0.3)

    # King safety
    wks = _king_safety(board, chess.WHITE, w_king_sq, w_pawns_mask, w_pawn_files, b_queens_mask)
    bks = _king_safety(board, chess.BLACK, b_king_sq, b_pawns_mask, b_pawn_files, w_queens_mask)
    mg += wks - bks
    eg += int((wks - bks) * 0.2)

    tapered = int(mg * mg_weight + eg * eg_weight)
    tapered += _mop_up(board, tapered)
    return tapered


def evaluate(board: chess.Board) -> int:
    """Side-to-move-relative evaluation in centipawns."""
    white_rel = evaluate_white_relative(board)
    return white_rel if board.turn == chess.WHITE else -white_rel
