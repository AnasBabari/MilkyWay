"""MilkyWay feature extraction: decomposes static evaluation into linear features.

For any board position:
    score ≈ beta . features + fixed_term
where:
    features: 50 canonical White-perspective features corresponding to TUNABLE_PARAM_NAMES
    beta: coefficient vector from EvalParameters
    fixed_term: piece-square table contribution + mop-up bonus
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constants import (  # noqa: E402
    MAX_PHASE,
    MW_0_2_EVAL,
    PHASE_WEIGHT_BISHOP,
    PHASE_WEIGHT_KNIGHT,
    PHASE_WEIGHT_QUEEN,
    PHASE_WEIGHT_ROOK,
    EvalParameters,
)
from evaluation import (  # noqa: E402
    _BLACK_PASSER_MASK_TUPLE,
    _WHITE_PASSER_MASK_TUPLE,
    _WHITE_PST_SQ,
    _mop_up,
    evaluate_white_relative,
)

FEATURE_SCHEMA_VERSION = "1.0.0"


def _extract_pawn_structure_counts(
    board: chess.Board,
    color: chess.Color,
    own_pawns: list[int],
    enemy_pawns_mask: int,
    file_counts: list[int],
) -> tuple[int, int, int, int, list[int], int, list[int]]:
    """Return pawn structure counts: doubled, isolated, backward, conn, passers, prot, list."""
    doubled = 0
    isolated = 0
    backward = 0
    connected = 0
    passers_by_adv = [0] * 8
    protected_passers = 0
    passers: list[int] = []

    passer_masks = _WHITE_PASSER_MASK_TUPLE if color == chess.WHITE else _BLACK_PASSER_MASK_TUPLE

    for sq in own_pawns:
        file = sq & 7
        rank = sq >> 3
        if file_counts[file] > 1:
            doubled += 1

        left = file_counts[file - 1] if file > 0 else 0
        right = file_counts[file + 1] if file < 7 else 0
        if left == 0 and right == 0:
            isolated += 1
        else:
            is_conn = False
            for nfile in (file - 1, file + 1):
                if 0 <= nfile < 8 and file_counts[nfile] > 0:
                    is_conn = True
                    break
            if is_conn and not (left == 0 and right == 0):
                connected += 1

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
                backward += 1

        if (enemy_pawns_mask & passer_masks[sq]) == 0:
            passers.append(sq)
            adv = rank if color == chess.WHITE else 7 - rank
            adv = max(0, min(7, adv))
            passers_by_adv[adv] += 1
            if board.is_attacked_by(color, sq):
                protected_passers += 1

    return (
        doubled,
        isolated,
        backward,
        connected,
        passers_by_adv,
        protected_passers,
        passers,
    )


def _extract_rook_counts(
    color: chess.Color,
    rook_sqs: list[int],
    own_pawn_files: list[int],
    enemy_pawn_files: list[int],
    passers: list[int],
) -> tuple[int, int, int, int, int]:
    """Returns (open_files, semi_open_files, seventh_rank, connected, behind_passers)."""
    open_files = 0
    semi_open_files = 0
    seventh = 0
    connected = 0
    behind = 0

    for sq in rook_sqs:
        file = sq & 7
        rank = sq >> 3
        own = own_pawn_files[file] > 0
        enemy = enemy_pawn_files[file] > 0
        if not own and not enemy:
            open_files += 1
        elif not own and enemy:
            semi_open_files += 1
        if (color == chess.WHITE and rank == 6) or (color == chess.BLACK and rank == 1):
            seventh += 1
        for other in rook_sqs:
            if other != sq and ((other >> 3) == rank or (other & 7) == file):
                connected += 1
                break
        for psq in passers:
            if (psq & 7) == file:
                prank = psq >> 3
                if color == chess.WHITE and rank < prank:
                    behind += 1
                    break
                if color == chess.BLACK and rank > prank:
                    behind += 1
                    break
    return open_files, semi_open_files, seventh, connected, behind


def _extract_king_safety_counts(
    board: chess.Board,
    color: chess.Color,
    king_sq: int | None,
    own_pawns_mask: int,
    own_pawn_files: list[int],
    enemy_queens_mask: int,
) -> tuple[int, int, int]:
    """Returns (missing_shields, open_files_near, attack_units)."""
    if king_sq is None:
        return 0, 0, 0
    enemy = not color
    kfile = king_sq & 7
    krank = king_sq >> 3

    missing_shields = 0
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
                    missing_shields += 1

    open_files_near = 0
    home = krank <= 1 if color == chess.WHITE else krank >= 6
    if home:
        for dfile in (-1, 0, 1):
            f = kfile + dfile
            if 0 <= f < 8 and own_pawn_files[f] == 0:
                open_files_near += 1

    attacks = 0
    for dfile in (-1, 0, 1):
        for drank in (-1, 0, 1):
            f = kfile + dfile
            r = krank + drank
            if 0 <= f < 8 and 0 <= r < 8 and board.is_attacked_by(enemy, (r << 3) | f):
                attacks += 1

    attack_units = attacks
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
            attack_units += 4 - min_qdist

    return missing_shields, open_files_near, attack_units


def extract_features_white(
    board: chess.Board,
    params: EvalParameters = MW_0_2_EVAL,
) -> tuple[list[float], float]:
    """Extract canonical White-perspective features and fixed term for board."""
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

    w_pawns: list[int] = []
    b_pawns: list[int] = []
    w_rooks: list[int] = []
    b_rooks: list[int] = []
    w_pawn_files = [0] * 8
    b_pawn_files = [0] * 8

    pst_mg = 0
    pst_eg = 0

    # Pawns
    bb = w_pawns_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        w_pawns.append(sq)
        idx = _WHITE_PST_SQ[sq]
        pst_mg += params.pawn_mg_pst[idx]
        pst_eg += params.pawn_eg_pst[idx]
        w_pawn_files[sq & 7] += 1

    bb = b_pawns_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        b_pawns.append(sq)
        idx = sq
        pst_mg -= params.pawn_mg_pst[idx]
        pst_eg -= params.pawn_eg_pst[idx]
        b_pawn_files[sq & 7] += 1

    # Knights
    w_n_att = 0
    bb = w_knights_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = _WHITE_PST_SQ[sq]
        pst_mg += params.knight_pst[idx]
        pst_eg += params.knight_pst[idx]
        w_n_att += board.attacks_mask(sq).bit_count()

    b_n_att = 0
    bb = b_knights_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = sq
        pst_mg -= params.knight_pst[idx]
        pst_eg -= params.knight_pst[idx]
        b_n_att += board.attacks_mask(sq).bit_count()

    # Bishops
    w_b_att = 0
    bb = w_bishops_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = _WHITE_PST_SQ[sq]
        pst_mg += params.bishop_pst[idx]
        pst_eg += params.bishop_pst[idx]
        w_b_att += board.attacks_mask(sq).bit_count()

    b_b_att = 0
    bb = b_bishops_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = sq
        pst_mg -= params.bishop_pst[idx]
        pst_eg -= params.bishop_pst[idx]
        b_b_att += board.attacks_mask(sq).bit_count()

    # Rooks
    w_r_att = 0
    bb = w_rooks_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        w_rooks.append(sq)
        idx = _WHITE_PST_SQ[sq]
        pst_mg += params.rook_pst[idx]
        pst_eg += params.rook_pst[idx]
        w_r_att += board.attacks_mask(sq).bit_count()

    b_r_att = 0
    bb = b_rooks_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        b_rooks.append(sq)
        idx = sq
        pst_mg -= params.rook_pst[idx]
        pst_eg -= params.rook_pst[idx]
        b_r_att += board.attacks_mask(sq).bit_count()

    # Queens
    w_q_att = 0
    bb = w_queens_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = _WHITE_PST_SQ[sq]
        pst_mg += params.queen_pst[idx]
        pst_eg += params.queen_pst[idx]
        w_q_att += board.attacks_mask(sq).bit_count()

    b_q_att = 0
    bb = b_queens_mask
    while bb:
        sq = (bb & -bb).bit_length() - 1
        bb ^= bb & -bb
        idx = sq
        pst_mg -= params.queen_pst[idx]
        pst_eg -= params.queen_pst[idx]
        b_q_att += board.attacks_mask(sq).bit_count()

    # Kings
    w_king_sq: int | None = None
    if w_king_mask:
        w_sq = (w_king_mask & -w_king_mask).bit_length() - 1
        w_king_sq = w_sq
        idx = _WHITE_PST_SQ[w_sq]
        pst_mg += params.king_mg_pst[idx]
        pst_eg += params.king_eg_pst[idx]

    b_king_sq: int | None = None
    if b_king_mask:
        b_sq = (b_king_mask & -b_king_mask).bit_length() - 1
        b_king_sq = b_sq
        idx = b_sq
        pst_mg -= params.king_mg_pst[idx]
        pst_eg -= params.king_eg_pst[idx]

    # Phase calculation
    w_knights = w_knights_mask.bit_count()
    b_knights = b_knights_mask.bit_count()
    w_bishops = w_bishops_mask.bit_count()
    b_bishops = b_bishops_mask.bit_count()
    w_rooks_cnt = w_rooks_mask.bit_count()
    b_rooks_cnt = b_rooks_mask.bit_count()
    w_queens = w_queens_mask.bit_count()
    b_queens = b_queens_mask.bit_count()

    phase = (
        (w_knights + b_knights) * PHASE_WEIGHT_KNIGHT
        + (w_bishops + b_bishops) * PHASE_WEIGHT_BISHOP
        + (w_rooks_cnt + b_rooks_cnt) * PHASE_WEIGHT_ROOK
        + (w_queens + b_queens) * PHASE_WEIGHT_QUEEN
    )
    phase = max(0, min(MAX_PHASE, phase))
    mg_w = phase / float(MAX_PHASE)
    eg_w = 1.0 - mg_w
    mob_w = 0.7 * mg_w + 0.3 * eg_w
    ks_w = 1.0 * mg_w + 0.2 * eg_w

    # Pawn structure counts
    w_d, w_i, w_bw, w_conn, w_p_adv, w_prot, w_passers = _extract_pawn_structure_counts(
        board, chess.WHITE, w_pawns, b_pawns_mask, w_pawn_files
    )
    b_d, b_i, b_bw, b_conn, b_p_adv, b_prot, b_passers = _extract_pawn_structure_counts(
        board, chess.BLACK, b_pawns, w_pawns_mask, b_pawn_files
    )

    # Rook counts
    w_open, w_semi, w_7th, w_rconn, w_behind = _extract_rook_counts(
        chess.WHITE, w_rooks, w_pawn_files, b_pawn_files, w_passers
    )
    b_open, b_semi, b_7th, b_rconn, b_behind = _extract_rook_counts(
        chess.BLACK, b_rooks, b_pawn_files, w_pawn_files, b_passers
    )

    # King safety counts
    w_sh_miss, w_of_near, w_att_u = _extract_king_safety_counts(
        board, chess.WHITE, w_king_sq, w_pawns_mask, w_pawn_files, b_queens_mask
    )
    b_sh_miss, b_of_near, b_att_u = _extract_king_safety_counts(
        board, chess.BLACK, b_king_sq, b_pawns_mask, b_pawn_files, w_queens_mask
    )

    # Bishop pair counts
    bp_w = 1 if w_bishops >= 2 else 0
    bp_b = 1 if b_bishops >= 2 else 0

    # Build 50-element feature vector matching TUNABLE_PARAM_NAMES
    features: list[float] = [
        # Material (12)
        (len(w_pawns) - len(b_pawns)) * mg_w,
        (len(w_pawns) - len(b_pawns)) * eg_w,
        (w_knights - b_knights) * mg_w,
        (w_knights - b_knights) * eg_w,
        (w_bishops - b_bishops) * mg_w,
        (w_bishops - b_bishops) * eg_w,
        (w_rooks_cnt - b_rooks_cnt) * mg_w,
        (w_rooks_cnt - b_rooks_cnt) * eg_w,
        (w_queens - b_queens) * mg_w,
        (w_queens - b_queens) * eg_w,
        (bp_w - bp_b) * mg_w,
        (bp_w - bp_b) * eg_w,
        # Mobility (4)
        (w_n_att - b_n_att) * mob_w,
        (w_b_att - b_b_att) * mob_w,
        (w_r_att - b_r_att) * mob_w,
        (w_q_att - b_q_att) * mob_w,
        # Pawn structure (8)
        (w_d - b_d) * mg_w,
        (w_d - b_d) * eg_w,
        (w_i - b_i) * mg_w,
        (w_i - b_i) * eg_w,
        (w_bw - b_bw) * 0.5 * mg_w,
        (w_bw - b_bw) * 0.5 * eg_w,
        (w_conn - b_conn) * mg_w,
        (w_conn - b_conn) * eg_w,
        # Passed pawns by rank 2..7 (12)
        (w_p_adv[1] - b_p_adv[1]) * mg_w,
        (w_p_adv[2] - b_p_adv[2]) * mg_w,
        (w_p_adv[3] - b_p_adv[3]) * mg_w,
        (w_p_adv[4] - b_p_adv[4]) * mg_w,
        (w_p_adv[5] - b_p_adv[5]) * mg_w,
        (w_p_adv[6] - b_p_adv[6]) * mg_w,
        (w_p_adv[1] - b_p_adv[1]) * eg_w,
        (w_p_adv[2] - b_p_adv[2]) * eg_w,
        (w_p_adv[3] - b_p_adv[3]) * eg_w,
        (w_p_adv[4] - b_p_adv[4]) * eg_w,
        (w_p_adv[5] - b_p_adv[5]) * eg_w,
        (w_p_adv[6] - b_p_adv[6]) * eg_w,
        # Protected passers (2)
        (w_prot - b_prot) * mg_w,
        (w_prot - b_prot) * eg_w,
        # Rook activity (9)
        (w_open - b_open) * mg_w,
        (w_open - b_open) * eg_w,
        (w_semi - b_semi) * mg_w,
        (w_semi - b_semi) * eg_w,
        (w_7th - b_7th) * mg_w,
        (w_7th - b_7th) * eg_w,
        (w_rconn - b_rconn) * mg_w,
        (w_behind - b_behind) * mg_w,
        (w_behind - b_behind) * eg_w,
        # King safety (3)
        (w_sh_miss - b_sh_miss) * ks_w,
        (w_of_near - b_of_near) * 0.5 * ks_w,
        (w_att_u - b_att_u) * ks_w,
    ]

    # Fixed terms: piece-square tables + mop up
    raw_eval = evaluate_white_relative(board, params)
    mop = _mop_up(board, raw_eval, params)
    fixed_term = float(pst_mg * mg_w + pst_eg * eg_w + mop)

    return features, fixed_term


def linear_predict_white(
    features: list[float],
    fixed_term: float,
    beta: list[float],
) -> float:
    """Compute score = beta . features + fixed_term."""
    dot = sum(f * b for f, b in zip(features, beta, strict=True))
    return dot + fixed_term


def main() -> None:
    parser = argparse.ArgumentParser(description="Feature extraction utility.")
    parser.add_argument("--fen", default=chess.STARTING_FEN)
    args = parser.parse_args()

    board = chess.Board(args.fen)
    features, fixed = extract_features_white(board)
    beta = MW_0_2_EVAL.get_tunable_vector()
    pred = linear_predict_white(features, fixed, beta)
    actual = evaluate_white_relative(board)

    print(f"FEN: {args.fen}")
    print(f"Features ({len(features)}): {features[:5]}... (first 5)")
    print(f"Fixed term: {fixed:.2f}")
    print(f"Linear predicted eval: {pred:.2f} (round: {round(pred)})")
    print(f"Actual MW-0.2 eval:    {actual}")
    print(f"Difference:            {actual - round(pred)} cp")


if __name__ == "__main__":
    main()
