"""MilkyWay M17 — Offline Stockfish labelling pipeline.

Evaluates positions using external Stockfish binary via UCI protocol.
Supports fixed node budgets (10k, 25k), MultiPV (default 4), mate handling,
and canonical score perspective (side-to-move).

NEVER commit the Stockfish executable.
Path is read from --stockfish or STOCKFISH_PATH environment variable.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.engine
import numpy as np

CANONICAL_PERSPECTIVE = "side_to_move"
DEFAULT_NODE_BUDGET = 10000
DEFAULT_MULTIPV = 4
MAX_CP_CLAMP = 1500.0


@dataclass
class StockfishLabel:
    best_move: str
    cp: float
    is_mate: bool
    mate_in: int | None
    top_k_moves: list[str]
    top_k_scores: list[float]
    wdl: list[float]  # [win, draw, loss] from side-to-move perspective


def score_to_wdl(cp: float) -> list[float]:
    """Convert centipawn score (side-to-move) to approximate WDL probabilities."""
    # Classical Lichess/Stockfish logistic model: P(win) = 1 / (1 + 10^(-cp / 400))
    # Draw probability peaks near 0 cp and decays as |cp| increases
    p_win = 1.0 / (1.0 + 10.0 ** (-cp / 400.0))
    # Approximate draw probability: ~0.4 at 0 cp, decaying with Gaussian
    p_draw = 0.40 * math.exp(-((cp / 300.0) ** 2))
    p_win_adj = max(0.0, p_win - p_draw / 2.0)
    p_loss_adj = max(0.0, (1.0 - p_win) - p_draw / 2.0)
    total = p_win_adj + p_draw + p_loss_adj
    return [float(p_win_adj / total), float(p_draw / total), float(p_loss_adj / total)]


def label_position(
    engine: chess.engine.SimpleEngine,
    fen: str,
    nodes: int = DEFAULT_NODE_BUDGET,
    multipv: int = DEFAULT_MULTIPV,
) -> StockfishLabel:
    """Run Stockfish analysis on a single FEN position."""
    board = chess.Board(fen)
    limit = chess.engine.Limit(nodes=nodes)

    infos = engine.analyse(board, limit, multipv=multipv)
    if not isinstance(infos, list):
        infos = [infos]

    top_moves: list[str] = []
    top_scores: list[float] = []

    best_move = ""
    best_cp = 0.0
    is_mate = False
    mate_in = None

    for i, info in enumerate(infos):
        pv = info.get("pv")
        if not pv:
            continue
        move_uci = pv[0].uci()
        top_moves.append(move_uci)

        score_obj = info.get("score")
        if score_obj is not None:
            pov_score = score_obj.pov(board.turn)
            if pov_score.is_mate():
                m = pov_score.mate()
                if i == 0:
                    is_mate = True
                    mate_in = m
                # Clamp forced mates to MAX_CP_CLAMP instead of ±100,000
                cp_val = MAX_CP_CLAMP if (m is not None and m > 0) else -MAX_CP_CLAMP
            else:
                raw_cp = pov_score.score()
                score_num = raw_cp if raw_cp is not None else 0.0
                cp_val = float(np.clip(score_num, -MAX_CP_CLAMP, MAX_CP_CLAMP))
        else:
            cp_val = 0.0

        top_scores.append(cp_val)
        if i == 0:
            best_move = move_uci
            best_cp = cp_val

    wdl = score_to_wdl(best_cp)

    return StockfishLabel(
        best_move=best_move,
        cp=best_cp,
        is_mate=is_mate,
        mate_in=mate_in,
        top_k_moves=top_moves,
        top_k_scores=top_scores,
        wdl=wdl,
    )


def resolve_stockfish_path(explicit_path: str | None = None) -> Path | None:
    """Find Stockfish executable from CLI arg or environment variable."""
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            return p
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="MilkyWay offline Stockfish labeller.")
    parser.add_argument("--stockfish", type=str, default=None, help="Path to Stockfish binary")
    parser.add_argument("--nodes", type=int, default=DEFAULT_NODE_BUDGET, help="Nodes per position")
    parser.add_argument("--multipv", type=int, default=DEFAULT_MULTIPV, help="MultiPV count")
    parser.add_argument("--limit-positions", type=int, default=100, help="Max positions to label")
    args = parser.parse_args()

    sf_path = resolve_stockfish_path(args.stockfish)
    if sf_path is None:
        print(
            "ERROR: Stockfish binary not found.\n"
            "Please specify via --stockfish <path> or set STOCKFISH_PATH environment variable.\n"
            "Offline labeller cannot proceed without the external binary.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Connecting to Stockfish at {sf_path} (nodes={args.nodes}, mpv={args.multipv})...")
    with chess.engine.SimpleEngine.popen_uci(str(sf_path)) as engine:
        test_fen = chess.STARTING_FEN
        label = label_position(engine, test_fen, nodes=args.nodes, multipv=args.multipv)
        msg = f"Startpos test: best={label.best_move}, cp={label.cp}, top={label.top_k_moves}"
        print(msg)


if __name__ == "__main__":
    main()
