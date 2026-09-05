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


def main() -> None:
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

    # Benchmark KS-A
    t0 = time.perf_counter()
    for b in boards:
        w_km = b.pieces_mask(chess.KING, chess.WHITE)
        w_sq = (w_km & -w_km).bit_length() - 1 if w_km else None
        ks_a(
            b,
            chess.WHITE,
            w_sq,
            b.pieces_mask(chess.PAWN, chess.WHITE),
            [1] * 8,
            b.pieces_mask(chess.QUEEN, chess.BLACK),
        )
    el_a = time.perf_counter() - t0

    # Benchmark KS-B
    t0 = time.perf_counter()
    for b in boards:
        w_km = b.pieces_mask(chess.KING, chess.WHITE)
        w_sq = (w_km & -w_km).bit_length() - 1 if w_km else None
        ks_b(
            b,
            chess.WHITE,
            w_sq,
            b.pieces_mask(chess.PAWN, chess.WHITE),
            [1] * 8,
            b.pieces_mask(chess.QUEEN, chess.BLACK),
        )
    el_b = time.perf_counter() - t0

    print(f"2000 positions: KS-A elapsed = {el_a*1000:.1f}ms ({len(boards)/el_a:.0f}/s)")
    print(f"2000 positions: KS-B elapsed = {el_b*1000:.1f}ms ({len(boards)/el_b:.0f}/s)")
    print(f"KS-B speedup: {el_a / el_b:.2f}x on king safety alone!")


if __name__ == "__main__":
    main()
