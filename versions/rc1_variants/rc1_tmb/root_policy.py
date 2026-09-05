"""MilkyWay M17 — Single-Core CPU Root Policy Evaluator.

Runs inference ONCE per move at the root of the search tree.
Scores and ranks legal moves using the distilled ONNX model.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

import chess
import numpy as np

try:
    import onnxruntime as ort  # type: ignore[import-untyped]
except ImportError:
    ort = None

DEFAULT_ONNX_PATH = Path(__file__).resolve().parent / "weights" / "milkyway_policy.onnx"

NUM_PLANES: int = 18
BOARD_SHAPE: tuple[int, int, int] = (NUM_PLANES, 8, 8)

PIECE_TO_PLANE: dict[tuple[chess.PieceType, chess.Color], int] = {
    (chess.PAWN, chess.WHITE): 0,
    (chess.KNIGHT, chess.WHITE): 1,
    (chess.BISHOP, chess.WHITE): 2,
    (chess.ROOK, chess.WHITE): 3,
    (chess.QUEEN, chess.WHITE): 4,
    (chess.KING, chess.WHITE): 5,
    (chess.PAWN, chess.BLACK): 6,
    (chess.KNIGHT, chess.BLACK): 7,
    (chess.BISHOP, chess.BLACK): 8,
    (chess.ROOK, chess.BLACK): 9,
    (chess.QUEEN, chess.BLACK): 10,
    (chess.KING, chess.BLACK): 11,
}

PLANE_TO_PIECE: dict[int, tuple[chess.PieceType, chess.Color]] = {
    v: k for k, v in PIECE_TO_PLANE.items()
}

PLANE_SIDE_TO_MOVE: int = 12
PLANE_CASTLE_WHITE_KINGSIDE: int = 13
PLANE_CASTLE_WHITE_QUEENSIDE: int = 14
PLANE_CASTLE_BLACK_KINGSIDE: int = 15
PLANE_CASTLE_BLACK_QUEENSIDE: int = 16
PLANE_EN_PASSANT: int = 17


def _build_move_vocabulary() -> tuple[list[str], dict[str, int]]:
    """Enumerate all 1968 geometrically possible UCI chess moves."""
    moves_set: set[str] = set()
    for from_sq in range(64):
        r1, f1 = divmod(from_sq, 8)
        for to_sq in range(64):
            r2, f2 = divmod(to_sq, 8)
            dr, df = abs(r2 - r1), abs(f2 - f1)

            is_ray = (r1 == r2 or f1 == f2 or dr == df) and (from_sq != to_sq)
            is_knight = (dr == 1 and df == 2) or (dr == 2 and df == 1)
            is_pawn_double = f1 == f2 and ((r1 == 1 and r2 == 3) or (r1 == 6 and r2 == 4))

            is_white_promo = r1 == 6 and r2 == 7 and df <= 1
            is_black_promo = r1 == 1 and r2 == 0 and df <= 1

            if is_white_promo or is_black_promo:
                for promo in ("q", "r", "b", "n"):
                    uci = f"{chess.square_name(from_sq)}{chess.square_name(to_sq)}{promo}"
                    moves_set.add(uci)
            if is_ray or is_knight or is_pawn_double:
                uci = f"{chess.square_name(from_sq)}{chess.square_name(to_sq)}"
                moves_set.add(uci)

    vocab = sorted(moves_set)
    mapping = {uci: idx for idx, uci in enumerate(vocab)}
    return vocab, mapping


VOCAB_INDEX_TO_UCI, VOCAB_UCI_TO_INDEX = _build_move_vocabulary()
MOVE_VOCABULARY_SIZE: int = len(VOCAB_INDEX_TO_UCI)


def move_to_index(move: chess.Move | str) -> int:
    """Map a chess.Move or UCI string to its vocabulary index [0, 1967]."""
    uci = move.uci() if isinstance(move, chess.Move) else move.lower()
    idx = VOCAB_UCI_TO_INDEX.get(uci)
    if idx is None:
        raise ValueError(f"Move '{uci}' is not in the legal UCI vocabulary")
    return idx


def index_to_uci(index: int) -> str:
    """Map a vocabulary index [0, 1967] to a UCI string."""
    if not (0 <= index < MOVE_VOCABULARY_SIZE):
        raise IndexError(f"Index {index} out of bounds for vocabulary size {MOVE_VOCABULARY_SIZE}")
    return VOCAB_INDEX_TO_UCI[index]


def index_to_move(index: int) -> chess.Move:
    """Map a vocabulary index [0, 1967] to a chess.Move object."""
    return chess.Move.from_uci(index_to_uci(index))


def board_to_tensor(board: chess.Board) -> np.ndarray:
    """Convert chess.Board to uint8 ndarray of shape (18, 8, 8)."""
    tensor = np.zeros(BOARD_SHAPE, dtype=np.uint8)

    for sq, piece in board.piece_map().items():
        plane = PIECE_TO_PLANE[(piece.piece_type, piece.color)]
        r, f = divmod(sq, 8)
        tensor[plane, r, f] = 1

    if board.turn == chess.WHITE:
        tensor[PLANE_SIDE_TO_MOVE, :, :] = 1

    if board.has_kingside_castling_rights(chess.WHITE):
        tensor[PLANE_CASTLE_WHITE_KINGSIDE, :, :] = 1
    if board.has_queenside_castling_rights(chess.WHITE):
        tensor[PLANE_CASTLE_WHITE_QUEENSIDE, :, :] = 1
    if board.has_kingside_castling_rights(chess.BLACK):
        tensor[PLANE_CASTLE_BLACK_KINGSIDE, :, :] = 1
    if board.has_queenside_castling_rights(chess.BLACK):
        tensor[PLANE_CASTLE_BLACK_QUEENSIDE, :, :] = 1

    if board.ep_square is not None:
        r, f = divmod(board.ep_square, 8)
        tensor[PLANE_EN_PASSANT, r, f] = 1

    return tensor


def fen_to_tensor(fen: str) -> np.ndarray:
    """Convert FEN string to uint8 ndarray of shape (18, 8, 8)."""
    board = chess.Board(fen)
    return board_to_tensor(board)


class RootPolicyEvaluator:
    """Evaluates policy distribution at root position using ONNX Runtime on 1 CPU core."""

    def __init__(self, model_path: Path | str | None = None) -> None:
        self.session: ort.InferenceSession | None = None
        self.input_name: str = ""
        self.output_name: str = ""
        self.enabled: bool = os.environ.get("MILKYWAY_ROOT_POLICY", "1") != "0"

        if not self.enabled or ort is None:
            return

        if model_path is None:
            model_path = DEFAULT_ONNX_PATH
        model_path = Path(model_path)

        if not model_path.is_file():
            self.enabled = False
            return

        try:
            sess_opts = ort.SessionOptions()
            sess_opts.intra_op_num_threads = 1
            sess_opts.inter_op_num_threads = 1
            sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            self.session = ort.InferenceSession(
                str(model_path), sess_opts, providers=["CPUExecutionProvider"]
            )
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
        except Exception:
            self.session = None
            self.enabled = False

    def is_available(self) -> bool:
        return self.enabled and self.session is not None

    def get_move_scores(
        self, board: chess.Board, legal_moves: list[chess.Move]
    ) -> dict[chess.Move, float]:
        """Compute policy logit / score for each legal move in the root position."""
        if not self.is_available() or self.session is None or not legal_moves:
            return {}

        try:
            # Shape: (1, 18, 8, 8)
            tensor = np.expand_dims(board_to_tensor(board).astype(np.float32), axis=0)
            logits = self.session.run([self.output_name], {self.input_name: tensor})[0][0]

            scores: dict[chess.Move, float] = {}
            for m in legal_moves:
                try:
                    idx = move_to_index(m)
                    scores[m] = float(logits[idx])
                except (ValueError, IndexError):
                    scores[m] = -100.0

            return scores
        except Exception:
            return {}


_GLOBAL_EVALUATOR: RootPolicyEvaluator | None = None


def get_root_evaluator() -> RootPolicyEvaluator:
    global _GLOBAL_EVALUATOR
    if _GLOBAL_EVALUATOR is None:
        _GLOBAL_EVALUATOR = RootPolicyEvaluator()
    return _GLOBAL_EVALUATOR


# Pre-warm evaluator during 90s init budget
with contextlib.suppress(Exception):
    get_root_evaluator()


