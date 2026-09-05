"""Benchmark King Safety variants (KS-A, KS-B, KS-C)."""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constants import (  # noqa: E402
    KING_ATTACK_UNIT,
    KING_MAX_SAFETY,
    KING_OPEN_FILE_NEAR,
    KING_SHIELD_MISSING,
)


def ks_a(
    board: chess.Board,
    color: chess.Color,
    king_sq: int | None,
    own_pawns_mask: int,
    own_pawn_files: list[int],
    enemy_queens_mask: int,
) -> int:
    """KS-A: Current full king safety."""
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
    # Enemy attacks near the king (9 is_attacked_by checks)
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


def ks_b(
    board: chess.Board,
    color: chess.Color,
    king_sq: int | None,
    own_pawns_mask: int,
    own_pawn_files: list[int],
    enemy_queens_mask: int,
) -> int:
    """KS-B: Simplified king safety.

    Uses shield + open files + queen proximity, omitting 9 is_attacked_by calls.
    """
    if king_sq is None:
        return 0
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


def ks_c(
    board: chess.Board,
    color: chess.Color,
    king_sq: int | None,
    own_pawns_mask: int,
    own_pawn_files: list[int],
    enemy_queens_mask: int,
    enemy_attacks_bb: int,
    enemy_pawns_mask: int,
) -> int:
    """KS-C: Fast bitboard king-zone attacks without is_attacked_by loops."""
    if king_sq is None:
        return 0
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
    # Fast bitboard king-zone attacks
    kzone = chess.BB_KING_ATTACKS[king_sq] | (1 << king_sq)
    if color == chess.BLACK:
        patt = (
            ((enemy_pawns_mask & 0x7F7F7F7F7F7F7F7F) << 7)
            | ((enemy_pawns_mask & 0xFEFEFEFEFEFEFEFE) << 9)
        )
    else:
        patt = (
            ((enemy_pawns_mask & 0x7F7F7F7F7F7F7F7F) >> 9)
            | ((enemy_pawns_mask & 0xFEFEFEFEFEFEFEFE) >> 7)
        )
    attacks = ((enemy_attacks_bb | patt) & kzone).bit_count()
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


def main() -> None:
    from constants import MW_0_2_EVAL, MW_0_2_KS_B, MW_0_2_KS_C
    from evaluation import evaluate_white_relative

    rng = random.Random(42)
    boards: list[chess.Board] = []
    for _ in range(2000):
        b = chess.Board()
        for _ in range(rng.randint(10, 60)):
            m = list(b.legal_moves)
            if not m or b.is_game_over():
                break
            b.push(rng.choice(m))
        boards.append(b)

    # Pre-extract masks for microbenchmarks
    data: list[tuple[chess.Board, int | None, int, int, int, int]] = []
    for b in boards:
        w_km = b.pieces_mask(chess.KING, chess.WHITE)
        w_sq = (w_km & -w_km).bit_length() - 1 if w_km else None
        w_pm = b.pieces_mask(chess.PAWN, chess.WHITE)
        b_qm = b.pieces_mask(chess.QUEEN, chess.BLACK)
        b_pm = b.pieces_mask(chess.PAWN, chess.BLACK)
        b_att = 0
        for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            bb = b.pieces_mask(pt, chess.BLACK)
            while bb:
                sq = (bb & -bb).bit_length() - 1
                bb ^= bb & -bb
                b_att |= b.attacks_mask(sq)
        data.append((b, w_sq, w_pm, b_qm, b_att, b_pm))

    # Benchmark KS-A isolated
    t0 = time.perf_counter()
    for b, w_sq, w_pm, b_qm, _b_att, _b_pm in data:
        ks_a(b, chess.WHITE, w_sq, w_pm, [1] * 8, b_qm)
    el_a = time.perf_counter() - t0

    # Benchmark KS-B isolated
    t0 = time.perf_counter()
    for b, w_sq, w_pm, b_qm, _b_att, _b_pm in data:
        ks_b(b, chess.WHITE, w_sq, w_pm, [1] * 8, b_qm)
    el_b = time.perf_counter() - t0

    # Benchmark KS-C isolated
    t0 = time.perf_counter()
    for b, w_sq, w_pm, b_qm, b_att, b_pm in data:
        ks_c(b, chess.WHITE, w_sq, w_pm, [1] * 8, b_qm, b_att, b_pm)
    el_c = time.perf_counter() - t0

    print("--- King Safety Microbenchmark (2000 positions, isolated) ---")
    rate_a = len(boards) / el_a
    rate_b = len(boards) / el_b
    rate_c = len(boards) / el_c
    print(f"KS-A: {el_a*1000:6.1f}ms ({rate_a:8.0f} call/s) [baseline 9 is_attacked_by loops]")
    print(f"KS-B: {el_b*1000:6.1f}ms ({rate_b:8.0f} call/s) [{el_a/el_b:.2f}x vs KS-A; simplified]")
    print(f"KS-C: {el_c*1000:6.1f}ms ({rate_c:8.0f} call/s) [{el_a/el_c:.2f}x vs KS-A; bitboards]")

    # Full evaluation throughput
    t0 = time.perf_counter()
    for b in boards:
        evaluate_white_relative(b, MW_0_2_EVAL)
    el_full_a = time.perf_counter() - t0

    t0 = time.perf_counter()
    for b in boards:
        evaluate_white_relative(b, MW_0_2_KS_B)
    el_full_b = time.perf_counter() - t0

    t0 = time.perf_counter()
    for b in boards:
        evaluate_white_relative(b, MW_0_2_KS_C)
    el_full_c = time.perf_counter() - t0

    pct_b = (el_full_a / el_full_b - 1) * 100
    pct_c = (el_full_a / el_full_c - 1) * 100
    r_full_a = len(boards) / el_full_a
    r_full_b = len(boards) / el_full_b
    r_full_c = len(boards) / el_full_c
    print("\n--- Full Static Evaluation Throughput (2000 positions) ---")
    print(f"MW-0.2 (KS-A) : {r_full_a:6.0f} eval/s ({el_full_a*1000:.1f}ms)")
    print(f"MW_0_2_KS_B   : {r_full_b:6.0f} eval/s ({el_full_b*1000:.1f}ms, +{pct_b:.1f}%)")
    print(f"MW_0_2_KS_C   : {r_full_c:6.0f} eval/s ({el_full_c*1000:.1f}ms, +{pct_c:.1f}%)")


if __name__ == "__main__":
    main()
