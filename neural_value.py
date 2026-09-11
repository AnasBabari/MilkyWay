"""Neural value evaluator using the flagship ONNX model.

Loads the joint policy+value ONNX and extracts the value head output,
converting WDL logits to centipawns for use in search.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import chess
import numpy as np

try:
    import onnxruntime as ort  # type: ignore[import-untyped]
except ImportError:
    ort = None

from root_policy import board_to_tensor

DEFAULT_ONNX_PATH = Path(__file__).resolve().parent / "weights" / "milkyway_flagship_v7.onnx"


def _wdl_logits_to_cp(wdl_logits: np.ndarray) -> int:
    """Convert 3-way WDL logits to centipawns (side-to-move relative)."""
    # Stable softmax
    max_logit = float(np.max(wdl_logits))
    exps = np.exp(wdl_logits - max_logit)
    probs = exps / np.sum(exps)
    p_win = float(probs[0])
    p_draw = float(probs[1])
    # Expected score
    e = p_win + 0.5 * p_draw
    e = max(0.001, min(0.999, e))
    cp = 400.0 * math.log10(e / (1.0 - e))
    return round(cp)


class NeuralValueEvaluator:
    """ONNX-based value head evaluator. One inference per root position."""

    def __init__(self, model_path: Path | str | None = None) -> None:
        self.session: ort.InferenceSession | None = None
        self.input_name: str = ""
        self.value_output_name: str = ""
        # Off by default: the 71% confirm validation was measured with the
        # speed build alone (no neural root value). The neural aspiration
        # bootstrap is still experimental and trended below baseline on the
        # pilot, so it stays opt-in until a full match proves it helps.
        self.enabled: bool = os.environ.get("MILKYWAY_NEURAL_VALUE", "0") != "0"

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
            # Find the value output (second output in flagship ONNX)
            outputs = self.session.get_outputs()
            if len(outputs) >= 2:
                self.value_output_name = outputs[1].name
            else:
                self.enabled = False
        except Exception:
            self.session = None
            self.enabled = False

    def is_available(self) -> bool:
        return self.enabled and self.session is not None

    def get_value(self, board: chess.Board) -> int | None:
        """Return neural cp estimate for the given board, or None if unavailable."""
        if not self.is_available() or self.session is None:
            return None
        try:
            tensor = np.expand_dims(board_to_tensor(board).astype(np.float32), axis=0)
            value_out = self.session.run(
                [self.value_output_name], {self.input_name: tensor}
            )[0][0]
            return _wdl_logits_to_cp(value_out)
        except Exception:
            return None


_GLOBAL_NEURAL_VALUE: NeuralValueEvaluator | None = None


def get_neural_value_evaluator() -> NeuralValueEvaluator:
    global _GLOBAL_NEURAL_VALUE
    if _GLOBAL_NEURAL_VALUE is None:
        _GLOBAL_NEURAL_VALUE = NeuralValueEvaluator()
    return _GLOBAL_NEURAL_VALUE
