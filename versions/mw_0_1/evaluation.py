"""MilkyWay tapered handcrafted evaluation (centipawns, side-to-move relative).

Design: one pass over the piece map for material + PST + phase, then cheap
structural terms from file counts and bitboard queries. No legal-move
generation here so leaf evaluation stays fast.
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


def _pst_index(square: int, color: chess.Color) -> int:
    rank = chess.square_rank(square)
    file = chess.square_file(square)
    if color == chess.WHITE:
        return (7 - rank) * 8 + file
    return rank * 8 + file


def _white_pawn_files(board: chess.Board, color: chess.Color) -> list[int]:
    """File counts for `color` pawns, indexed 0..7."""
    counts = [0] * 8
    for sq in board.pieces(chess.PAWN, color):
        counts[chess.square_file(sq)] += 1
    return counts


def _is_passed(sq: int, color: chess.Color, enemy_pawn_sqs: set[int]) -> bool:
    file = chess.square_file(sq)
    rank = chess.square_rank(sq)
    for esq in enemy_pawn_sqs:
        efile = chess.square_file(esq)
        erank = chess.square_rank(esq)
        if abs(efile - file) > 1:
            continue
        if color == chess.WHITE and erank > rank:
            return False
        if color == chess.BLACK and erank < rank:
            return False
    return True


def _pawn_structure(
    board: chess.Board,
    color: chess.Color,
    own_pawns: set[int],
    enemy_pawns: set[int],
    file_counts: list[int],
    enemy_file_counts: list[int],
) -> tuple[int, int]:
    mg = 0
    eg = 0
    for sq in own_pawns:
        file = chess.square_file(sq)
        rank = chess.square_rank(sq)
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
                # Only award when not isolated (already penalised above).
                mg += CONNECTED_PAWN_MG
                eg += CONNECTED_PAWN_EG
        # Backward: simplified — own pawn, no own pawn behind on neighbouring
        # files, and an enemy pawn ahead on a neighbouring file could attack.
        # Keep it cheap and conservative.
        if left == 0 and right == 0:
            pass  # already isolated; skip extra backward penalty
        else:
            behind_rank_ok = False
            for nfile in (file - 1, file + 1):
                if 0 <= nfile < 8:
                    for osq in own_pawns:
                        if chess.square_file(osq) == nfile:
                            orank = chess.square_rank(osq)
                            if color == chess.WHITE and orank < rank:
                                behind_rank_ok = True
                            if color == chess.BLACK and orank > rank:
                                behind_rank_ok = True
            if not behind_rank_ok:
                mg += BACKWARD_PAWN_MG // 2
                eg += BACKWARD_PAWN_EG // 2
        # Passed pawns.
        if _is_passed(sq, color, enemy_pawns):
            adv = rank if color == chess.WHITE else 7 - rank
            adv = max(0, min(7, adv))
            mg += PASSED_PAWN_MG[adv]
            eg += PASSED_PAWN_EG[adv]
            if board.is_attacked_by(color, sq):
                mg += PROTECTED_PASSER_MG
                eg += PROTECTED_PASSER_EG
    # Silence unused-arg warning shape (kept for future tuning hooks).
    _ = enemy_file_counts
    return mg, eg


def _rook_terms(
    board: chess.Board,
    color: chess.Color,
    rook_sqs: list[int],
    own_pawn_files: list[int],
    enemy_pawn_files: list[int],
    enemy_pawns: set[int],
    own_pawns: set[int],
) -> tuple[int, int]:
    mg = 0
    eg = 0
    rook_set = set(rook_sqs)
    for sq in rook_sqs:
        file = chess.square_file(sq)
        rank = chess.square_rank(sq)
        own = own_pawn_files[file] > 0
        enemy = enemy_pawn_files[file] > 0
        if not own and not enemy:
            mg += ROOK_OPEN_FILE_MG
            eg += ROOK_OPEN_FILE_EG
        elif not own and enemy:
            mg += ROOK_SEMI_OPEN_MG
            eg += ROOK_SEMI_OPEN_EG
        # Seventh rank (white: rank index 6; black: rank index 1).
        if (color == chess.WHITE and rank == 6) or (color == chess.BLACK and rank == 1):
            mg += ROOK_SEVENTH_MG
            eg += ROOK_SEVENTH_EG
        # Connected rooks: another rook aligned on rank/file (cheap check).
        for other in rook_sqs:
            if other == sq:
                continue
            if chess.square_rank(other) == rank or chess.square_file(other) == file:
                mg += ROOK_CONNECTED_MG
                break
        # Rook behind passed pawn (own passer on same file).
        for psq in own_pawns:
            if chess.square_file(psq) != file:
                continue
            if not _is_passed(psq, color, enemy_pawns):
                continue
            prank = chess.square_rank(psq)
            if color == chess.WHITE and rank < prank:
                mg += ROOK_BEHIND_PASSER_MG
                eg += ROOK_BEHIND_PASSER_EG
                break
            if color == chess.BLACK and rank > prank:
                mg += ROOK_BEHIND_PASSER_MG
                eg += ROOK_BEHIND_PASSER_EG
                break
    _ = rook_set
    return mg, eg


def _mobility(board: chess.Board, color: chess.Color) -> int:
    total = 0
    for sq, piece in board.piece_map().items():
        if piece.color != color:
            continue
        if piece.piece_type == chess.KNIGHT:
            total += MOBILITY_KNIGHT * len(board.attacks(sq))
        elif piece.piece_type == chess.BISHOP:
            total += MOBILITY_BISHOP * len(board.attacks(sq))
        elif piece.piece_type == chess.ROOK:
            total += MOBILITY_ROOK * len(board.attacks(sq))
        elif piece.piece_type == chess.QUEEN:
            total += MOBILITY_QUEEN * len(board.attacks(sq))
    return total


def _king_safety(board: chess.Board, color: chess.Color) -> int:
    try:
        king_sq = board.king(color)
    except ValueError:
        return 0
    if king_sq is None:
        return 0
    enemy = not color
    score = 0
    kfile = chess.square_file(king_sq)
    krank = chess.square_rank(king_sq)
    # Pawn shield: expected pawn squares in front of the king.
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
                    psq = chess.square(f, r)
                    piece = board.piece_at(psq)
                    if (
                        piece is not None
                        and piece.piece_type == chess.PAWN
                        and piece.color == color
                    ):
                        shielded = True
                        break
                if not shielded:
                    score += KING_SHIELD_MISSING
    # Open files near the king (only when king is on its side of the board).
    home = krank <= 1 if color == chess.WHITE else krank >= 6
    if home:
        for dfile in (-1, 0, 1):
            f = kfile + dfile
            if 0 <= f < 8:
                has_own_pawn = any(
                    chess.square_file(sq) == f for sq in board.pieces(chess.PAWN, color)
                )
                if not has_own_pawn:
                    score += KING_OPEN_FILE_NEAR // 2
    # Enemy attacks near the king.
    attacks = 0
    for dfile in (-1, 0, 1):
        for drank in (-1, 0, 1):
            f = kfile + dfile
            r = krank + drank
            if 0 <= f < 8 and 0 <= r < 8 and board.is_attacked_by(enemy, chess.square(f, r)):
                attacks += 1
    score += KING_ATTACK_UNIT * attacks
    # Enemy queen proximity (cheap distance term).
    enemy_queens = list(board.pieces(chess.QUEEN, enemy))
    if enemy_queens:
        qdist = min(
            abs(chess.square_file(q) - kfile) + abs(chess.square_rank(q) - krank)
            for q in enemy_queens
        )
        if qdist <= 3:
            score += KING_ATTACK_UNIT * (4 - qdist)
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
    lfile = chess.square_file(loser_king)
    lrank = chess.square_rank(loser_king)
    edge = min(lfile, 7 - lfile) + min(lrank, 7 - lrank)
    proximity = abs(chess.square_file(winner_king) - lfile) + abs(
        chess.square_rank(winner_king) - lrank
    )
    # Smaller edge distance (near edge) is good; smaller proximity is good.
    bonus = (6 - edge) * MOP_EDGE_WEIGHT + (14 - proximity) * MOP_PROXIMITY_WEIGHT
    return bonus if winning_white else -bonus


def evaluate_white_relative(board: chess.Board) -> int:
    """White-relative static evaluation in centipawns (no mate scores)."""
    mg = 0
    eg = 0
    phase = 0

    piece_map = board.piece_map()
    white_pawns: set[int] = set()
    black_pawns: set[int] = set()
    white_rooks: list[int] = []
    black_rooks: list[int] = []
    white_bishops = 0
    black_bishops = 0

    for sq, piece in piece_map.items():
        pt = piece.piece_type
        color = piece.color
        sign = 1 if color == chess.WHITE else -1
        if pt == chess.PAWN:
            mg += sign * (PAWN_VALUE + PAWN_MG[_pst_index(sq, color)])
            eg += sign * (PAWN_VALUE + PAWN_EG[_pst_index(sq, color)])
            if color == chess.WHITE:
                white_pawns.add(sq)
            else:
                black_pawns.add(sq)
        elif pt == chess.KNIGHT:
            mg += sign * (KNIGHT_VALUE + KNIGHT_PST[_pst_index(sq, color)])
            eg += sign * (KNIGHT_VALUE + KNIGHT_PST[_pst_index(sq, color)])
            phase += PHASE_WEIGHT_KNIGHT
        elif pt == chess.BISHOP:
            mg += sign * (BISHOP_VALUE + BISHOP_PST[_pst_index(sq, color)])
            eg += sign * (BISHOP_VALUE + BISHOP_PST[_pst_index(sq, color)])
            phase += PHASE_WEIGHT_BISHOP
            if color == chess.WHITE:
                white_bishops += 1
            else:
                black_bishops += 1
        elif pt == chess.ROOK:
            mg += sign * (ROOK_VALUE + ROOK_PST[_pst_index(sq, color)])
            eg += sign * (ROOK_VALUE + ROOK_PST[_pst_index(sq, color)])
            phase += PHASE_WEIGHT_ROOK
            if color == chess.WHITE:
                white_rooks.append(sq)
            else:
                black_rooks.append(sq)
        elif pt == chess.QUEEN:
            mg += sign * (QUEEN_VALUE + QUEEN_PST[_pst_index(sq, color)])
            eg += sign * (QUEEN_VALUE + QUEEN_PST[_pst_index(sq, color)])
            phase += PHASE_WEIGHT_QUEEN
        elif pt == chess.KING:
            mg += sign * KING_MG[_pst_index(sq, color)]
            eg += sign * KING_EG[_pst_index(sq, color)]

    phase = max(0, min(MAX_PHASE, phase))
    mg_weight = phase / MAX_PHASE
    eg_weight = 1.0 - mg_weight

    # Bishop pair.
    if white_bishops >= 2:
        mg += BISHOP_PAIR_MG
        eg += BISHOP_PAIR_EG
    if black_bishops >= 2:
        mg -= BISHOP_PAIR_MG
        eg -= BISHOP_PAIR_EG

    white_pawn_files = _white_pawn_files(board, chess.WHITE)
    black_pawn_files = _white_pawn_files(board, chess.BLACK)

    wpmg, wpeg = _pawn_structure(
        board, chess.WHITE, white_pawns, black_pawns, white_pawn_files, black_pawn_files
    )
    bpmg, bpeg = _pawn_structure(
        board, chess.BLACK, black_pawns, white_pawns, black_pawn_files, white_pawn_files
    )
    mg += wpmg - bpmg
    eg += wpeg - bpeg

    wrmg, wreg = _rook_terms(
        board,
        chess.WHITE,
        white_rooks,
        white_pawn_files,
        black_pawn_files,
        black_pawns,
        white_pawns,
    )
    brmg, breg = _rook_terms(
        board,
        chess.BLACK,
        black_rooks,
        black_pawn_files,
        white_pawn_files,
        white_pawns,
        black_pawns,
    )
    mg += wrmg - brmg
    eg += wreg - breg

    # Mobility (tapered lightly toward middlegame).
    mob = _mobility(board, chess.WHITE) - _mobility(board, chess.BLACK)
    mg += int(mob * 0.7)
    eg += int(mob * 0.3)

    # King safety fades in the endgame.
    wks = _king_safety(board, chess.WHITE)
    bks = _king_safety(board, chess.BLACK)
    mg += wks - bks
    # eg gets only 20% of the king-safety term.
    eg += int((wks - bks) * 0.2)

    tapered = int(mg * mg_weight + eg * eg_weight)
    tapered += _mop_up(board, tapered)
    return tapered


def evaluate(board: chess.Board) -> int:
    """Side-to-move-relative evaluation in centipawns."""
    white_rel = evaluate_white_relative(board)
    return white_rel if board.turn == chess.WHITE else -white_rel
