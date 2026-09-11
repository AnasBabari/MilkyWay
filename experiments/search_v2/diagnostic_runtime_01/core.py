"""Team-written array-board move generation for a compiled search prototype.

Squares are a1=0 through h8=63; signed pieces use pawn=1 through king=6.
No third-party engine implementation or tables are used.
"""
from __future__ import annotations

import numpy as np
from numba import njit

KNIGHT_STEPS = ((1, 2), (2, 1), (2, -1), (1, -2),
                (-1, -2), (-2, -1), (-2, 1), (-1, 2))
DIRECTIONS = ((1, 1), (1, -1), (-1, 1), (-1, -1),
              (1, 0), (-1, 0), (0, 1), (0, -1))


@njit(cache=False)
def attacked(board, square, by):
    rank, file = square // 8, square % 8
    pawn_rank = rank - by
    if 0 <= pawn_rank < 8:
        for df in (-1, 1):
            f = file + df
            if 0 <= f < 8 and board[pawn_rank * 8 + f] == by:
                return True
    for dr, df in KNIGHT_STEPS:
        r, f = rank + dr, file + df
        if 0 <= r < 8 and 0 <= f < 8 and board[r * 8 + f] == by * 2:
            return True
    for direction in range(8):
        dr, df = DIRECTIONS[direction]
        r, f = rank + dr, file + df
        distance = 1
        while 0 <= r < 8 and 0 <= f < 8:
            piece = int(board[r * 8 + f])
            if piece:
                if piece * by > 0:
                    kind = abs(piece)
                    if kind == 5 or (kind == 3 and direction < 4):
                        return True
                    if (kind == 4 and direction >= 4) or (kind == 6 and distance == 1):
                        return True
                break
            r += dr
            f += df
            distance += 1
    return False


@njit(cache=False)
def king_square(board, side):
    for square in range(64):
        if board[square] == side * 6:
            return square
    return -1


@njit(cache=False)
def make_move(board, move, rights, ep):
    origin, target, promotion = move & 63, (move >> 6) & 63, move >> 12
    piece, captured = int(board[origin]), int(board[target])
    side = 1 if piece > 0 else -1
    ep_capture = -1
    ep_piece = 0
    rook_from = -1
    rook_to = -1
    rook_piece = 0
    if abs(piece) == 1 and target == ep and captured == 0 and origin % 8 != target % 8:
        ep_capture = target - 8 * side
        ep_piece = int(board[ep_capture])
        board[ep_capture] = 0
    board[origin] = 0
    board[target] = side * promotion if promotion else piece
    if abs(piece) == 6:
        rights &= 12 if side == 1 else 3
        if abs(target - origin) == 2:
            rook_from = origin + 3 if target > origin else origin - 4
            rook_to = origin + 1 if target > origin else origin - 1
            rook_piece = int(board[rook_from])
            board[rook_from] = 0
            board[rook_to] = rook_piece
    for corner, mask in ((0, 2), (7, 1), (56, 8), (63, 4)):
        if origin == corner or target == corner:
            rights &= ~mask
    new_ep = (origin + target) // 2 if abs(piece) == 1 and abs(target - origin) == 16 else -1
    return (piece, captured, ep_capture, ep_piece, rook_from, rook_to, rook_piece, rights, new_ep)


@njit(cache=False)
def unmake_move(board, move, undo):
    origin, target = move & 63, (move >> 6) & 63
    board[origin], board[target] = undo[0], undo[1]
    if undo[2] >= 0:
        board[undo[2]] = undo[3]
    if undo[4] >= 0:
        board[undo[4]], board[undo[5]] = undo[6], 0


@njit(cache=False)
def generate(board, side, rights, ep, captures_only=False):
    moves = np.empty(512, dtype=np.int64)
    count = 0
    for origin in range(64):
        piece = int(board[origin])
        if piece * side <= 0:
            continue
        kind = abs(piece)
        rank, file = origin // 8, origin % 8
        if kind == 1:
            r = rank + side
            if not 0 <= r < 8:
                continue
            target = r * 8 + file
            promoting = r == 0 or r == 7
            if board[target] == 0 and (not captures_only or promoting):
                if promoting:
                    for promo in (2, 3, 4, 5):
                        moves[count] = origin | (target << 6) | (promo << 12)
                        count += 1
                else:
                    moves[count] = origin | (target << 6)
                    count += 1
                    if rank == (1 if side == 1 else 6):
                        double = target + side * 8
                        if board[double] == 0:
                            moves[count] = origin | (double << 6)
                            count += 1
            for df in (-1, 1):
                f = file + df
                if not 0 <= f < 8:
                    continue
                target = r * 8 + f
                enemy = int(board[target])
                if (enemy * side < 0 and abs(enemy) != 6) or (
                    target == ep and enemy == 0 and board[target - side * 8] == -side
                ):
                    if promoting:
                        for promo in (2, 3, 4, 5):
                            moves[count] = origin | (target << 6) | (promo << 12)
                            count += 1
                    else:
                        moves[count] = origin | (target << 6)
                        count += 1
        elif kind == 2:
            for dr, df in KNIGHT_STEPS:
                r, f = rank + dr, file + df
                if not (0 <= r < 8 and 0 <= f < 8):
                    continue
                target = r * 8 + f
                enemy = int(board[target])
                if enemy * side <= 0 and abs(enemy) != 6 and (enemy or not captures_only):
                    moves[count] = origin | (target << 6)
                    count += 1
        else:
            begin = 4 if kind == 4 else 0
            end = 4 if kind == 3 else 8
            for direction in range(begin, end):
                dr, df = DIRECTIONS[direction]
                r, f = rank + dr, file + df
                while 0 <= r < 8 and 0 <= f < 8:
                    target = r * 8 + f
                    enemy = int(board[target])
                    if enemy * side > 0 or abs(enemy) == 6:
                        break
                    if enemy or not captures_only:
                        moves[count] = origin | (target << 6)
                        count += 1
                    if enemy or kind == 6:
                        break
                    r += dr
                    f += df
            if kind == 6 and not captures_only:
                home = 4 if side == 1 else 60
                king_flag, queen_flag = ((1, 2) if side == 1 else (4, 8))
                if origin == home and not attacked(board, home, -side):
                    if (rights & king_flag and board[home + 1] == 0 and board[home + 2] == 0
                            and board[home + 3] == side * 4
                            and not attacked(board, home + 1, -side)
                            and not attacked(board, home + 2, -side)):
                        moves[count] = home | ((home + 2) << 6)
                        count += 1
                    if (rights & queen_flag and board[home - 1] == 0 and board[home - 2] == 0
                            and board[home - 3] == 0 and board[home - 4] == side * 4
                            and not attacked(board, home - 1, -side)
                            and not attacked(board, home - 2, -side)):
                        moves[count] = home | ((home - 2) << 6)
                        count += 1
    return moves, count


@njit(cache=False)
def legal_moves(board, side, rights, ep):
    moves, count = generate(board, side, rights, ep)
    king = king_square(board, side)
    kept = 0
    for i in range(count):
        move = moves[i]
        undo = make_move(board, move, rights, ep)
        square = (move >> 6) & 63 if abs(undo[0]) == 6 else king
        valid = not attacked(board, square, -side)
        unmake_move(board, move, undo)
        if valid:
            moves[kept] = move
            kept += 1
    return moves[:kept]


@njit(cache=False)
def perft(board, side, rights, ep, depth):
    if depth == 0:
        return 1
    moves, count = generate(board, side, rights, ep)
    king = king_square(board, side)
    total = 0
    for i in range(count):
        move = moves[i]
        undo = make_move(board, move, rights, ep)
        square = (move >> 6) & 63 if abs(undo[0]) == 6 else king
        if not attacked(board, square, -side):
            total += perft(board, -side, undo[7], undo[8], depth - 1)
        unmake_move(board, move, undo)
    return total


def encode_board(board):
    array = np.zeros(64, dtype=np.int8)
    for square, piece in board.piece_map().items():
        array[square] = piece.piece_type * (1 if piece.color else -1)
    rights = (int(board.has_kingside_castling_rights(True))
              | int(board.has_queenside_castling_rights(True)) << 1
              | int(board.has_kingside_castling_rights(False)) << 2
              | int(board.has_queenside_castling_rights(False)) << 3)
    ep = board.ep_square if board.ep_square is not None else -1
    return array, 1 if board.turn else -1, rights, ep
