"""Unit tests for M17 chess position and move representation."""

from __future__ import annotations

import chess
import numpy as np
import pytest  # type: ignore[import-not-found]

from training.data.representation import (
    MOVE_VOCABULARY_SIZE,
    board_to_tensor,
    fen_to_tensor,
    index_to_move,
    index_to_uci,
    move_to_index,
    tensor_to_board,
)


def test_vocabulary_completeness_and_bijection() -> None:
    assert MOVE_VOCABULARY_SIZE == 1968
    seen_indices = set()
    seen_ucis = set()

    for idx in range(MOVE_VOCABULARY_SIZE):
        uci = index_to_uci(idx)
        assert uci not in seen_ucis
        seen_ucis.add(uci)

        move = index_to_move(idx)
        assert move.uci() == uci

        mapped_idx = move_to_index(move)
        assert mapped_idx == idx
        assert mapped_idx not in seen_indices
        seen_indices.add(mapped_idx)

        str_idx = move_to_index(uci)
        assert str_idx == idx

    assert len(seen_indices) == 1968


def test_move_categories() -> None:
    # Quiet move
    m_quiet = chess.Move.from_uci("e2e4")
    idx_quiet = move_to_index(m_quiet)
    assert index_to_uci(idx_quiet) == "e2e4"

    # Capture
    m_capture = chess.Move.from_uci("e4d5")
    idx_capture = move_to_index(m_capture)
    assert index_to_uci(idx_capture) == "e4d5"

    # Castle kingside (white & black)
    m_castle_w_k = chess.Move.from_uci("e1g1")
    idx_w_k = move_to_index(m_castle_w_k)
    assert index_to_uci(idx_w_k) == "e1g1"

    m_castle_b_k = chess.Move.from_uci("e8g8")
    idx_b_k = move_to_index(m_castle_b_k)
    assert index_to_uci(idx_b_k) == "e8g8"

    # Castle queenside (white & black)
    m_castle_w_q = chess.Move.from_uci("e1c1")
    idx_w_q = move_to_index(m_castle_w_q)
    assert index_to_uci(idx_w_q) == "e1c1"

    m_castle_b_q = chess.Move.from_uci("e8c8")
    idx_b_q = move_to_index(m_castle_b_q)
    assert index_to_uci(idx_b_q) == "e8c8"

    # En passant (diagonal pawn capture)
    m_ep = chess.Move.from_uci("e5d6")
    idx_ep = move_to_index(m_ep)
    assert index_to_uci(idx_ep) == "e5d6"

    # Promotions: Queen, Rook, Bishop, Knight (White)
    for promo, promo_char in [
        (chess.QUEEN, "q"),
        (chess.ROOK, "r"),
        (chess.BISHOP, "b"),
        (chess.KNIGHT, "n"),
    ]:
        m_promo = chess.Move(chess.E7, chess.E8, promotion=promo)
        idx_promo = move_to_index(m_promo)
        assert index_to_uci(idx_promo) == f"e7e8{promo_char}"

    # Promotions: Queen, Rook, Bishop, Knight (Black)
    for promo, promo_char in [
        (chess.QUEEN, "q"),
        (chess.ROOK, "r"),
        (chess.BISHOP, "b"),
        (chess.KNIGHT, "n"),
    ]:
        m_promo_b = chess.Move(chess.A2, chess.A1, promotion=promo)
        idx_promo_b = move_to_index(m_promo_b)
        assert index_to_uci(idx_promo_b) == f"a2a1{promo_char}"


def test_invalid_move_and_index_handling() -> None:
    with pytest.raises(ValueError):
        move_to_index("e2e9")  # illegal square

    with pytest.raises(IndexError):
        index_to_uci(-1)

    with pytest.raises(IndexError):
        index_to_uci(1968)


def test_board_tensor_conversion_startpos() -> None:
    board = chess.Board()
    tensor = board_to_tensor(board)

    assert tensor.shape == (18, 8, 8)
    assert tensor.dtype == np.uint8

    # White pawns on rank 2 (index 1)
    assert np.sum(tensor[0]) == 8
    assert np.all(tensor[0, 1, :] == 1)

    # Black pawns on rank 7 (index 6)
    assert np.sum(tensor[6]) == 8
    assert np.all(tensor[6, 6, :] == 1)

    # Side to move: White (all 1s)
    assert np.all(tensor[12] == 1)

    # Castling rights all 1s
    assert np.all(tensor[13] == 1)
    assert np.all(tensor[14] == 1)
    assert np.all(tensor[15] == 1)
    assert np.all(tensor[16] == 1)

    # No en passant
    assert np.all(tensor[17] == 0)

    # Reconstruct board
    reconstructed = tensor_to_board(tensor)
    assert reconstructed.piece_map() == board.piece_map()
    assert reconstructed.turn == board.turn
    assert reconstructed.castling_rights == board.castling_rights
    assert reconstructed.ep_square == board.ep_square


def test_board_tensor_conversion_complex_fen() -> None:
    # Position with en passant and partial castling
    fen = "r1bqk2r/pp2bppp/2n1pn2/2ppP3/3P4/2PB1N2/PP3PPP/RNBQ1RK1 b kq d6 0 8"
    board = chess.Board(fen)
    tensor = fen_to_tensor(fen)

    assert tensor.shape == (18, 8, 8)

    # Black to move: plane 12 must be 0
    assert np.all(tensor[12] == 0)

    # Castling: White has no castling rights (0), Black has kq (13=0, 14=0, 15=1, 16=1)
    assert np.all(tensor[13] == 0)
    assert np.all(tensor[14] == 0)
    assert np.all(tensor[15] == 1)
    assert np.all(tensor[16] == 1)

    # En passant square: d6 (sq = 5 * 8 + 3 = 43)
    assert tensor[17, 5, 3] == 1
    assert np.sum(tensor[17]) == 1

    # Reconstruct
    rec = tensor_to_board(tensor)
    assert rec.piece_map() == board.piece_map()
    assert rec.turn == board.turn
    assert rec.castling_rights == board.castling_rights
    assert rec.ep_square == board.ep_square


def test_larpmaxx_failure_position_tensor() -> None:
    fen = "1rBq1r2/1p3p1k/2n3pb/p1p4p/P3Pp1P/3P2P1/1PPQ1P2/R2R2K1 w - - 0 19"
    board = chess.Board(fen)
    tensor = fen_to_tensor(fen)

    assert np.all(tensor[12] == 1)  # White to move
    assert np.all(tensor[13:17] == 0)  # No castling rights for anyone
    assert np.all(tensor[17] == 0)  # No ep square

    rec = tensor_to_board(tensor)
    assert rec.piece_map() == board.piece_map()
    assert rec.turn == chess.WHITE
