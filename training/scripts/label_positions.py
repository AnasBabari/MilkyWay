"""Offline Stockfish position labeller for MilkyWay evaluation tuning.

Labels positions with reproducible Stockfish search scores converted
to canonical White-perspective centipawns.

Features:
- Configurable fixed node/depth budget for reproducibility
- Canonical White-perspective conversion:
    if turn == BLACK: sf_cp_white = -score_cp
- Mate detection and separation
- Centipawn clamping (default: [-1500, +1500] cp)
- Mock engine fallback when Stockfish binary is not present in development
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import chess
import chess.engine

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation import evaluate_white_relative  # noqa: E402

DEFAULT_NODE_BUDGET = 25000
CP_CLAMP_MIN = -1500
CP_CLAMP_MAX = 1500


def find_stockfish_executable(custom_path: str | None = None) -> str | None:
    """Detect Stockfish executable from CLI arg, env var, or PATH."""
    if custom_path and Path(custom_path).is_file():
        return custom_path

    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path and Path(env_path).is_file():
        return env_path

    # Common system PATH check
    import shutil

    which = shutil.which("stockfish")
    if which:
        return which

    return None


def mock_label_position(board: chess.Board) -> dict[str, Any]:
    """Deterministic mock labeler when external engine is absent.

    Uses a sound 1-ply minimax lookahead over legal moves without multi-move
    summation or inverted piece-value heuristics.
    """
    if board.is_checkmate():
        score_white = -30000 if board.turn == chess.WHITE else 30000
        return {
            "sf_cp_white": max(CP_CLAMP_MIN, min(CP_CLAMP_MAX, score_white)),
            "raw_cp": score_white,
            "is_mate": True,
            "mate_moves": 0,
            "sf_nodes": 1,
            "sf_depth": 1,
            "label_engine": "mock_evaluator_v2",
        }
    if board.is_stalemate() or board.is_insufficient_material():
        return {
            "sf_cp_white": 0,
            "raw_cp": 0,
            "is_mate": False,
            "mate_moves": None,
            "sf_nodes": 1,
            "sf_depth": 1,
            "label_engine": "mock_evaluator_v2",
        }

    base_eval = evaluate_white_relative(board)
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        score_white = base_eval
    else:
        # 1-ply lookahead: side to move optimizes White-relative evaluation
        best_eval = -999999 if board.turn == chess.WHITE else 999999
        for move in legal_moves:
            board.push(move)
            v = evaluate_white_relative(board)
            board.pop()
            if board.turn == chess.WHITE:
                if v > best_eval:
                    best_eval = v
            else:
                if v < best_eval:
                    best_eval = v
        # Blend shallow lookahead with static base
        score_white = int(0.5 * base_eval + 0.5 * best_eval)

    clamped_white = max(CP_CLAMP_MIN, min(CP_CLAMP_MAX, score_white))
    return {
        "sf_cp_white": clamped_white,
        "raw_cp": score_white,
        "is_mate": False,
        "mate_moves": None,
        "sf_nodes": len(legal_moves),
        "sf_depth": 1,
        "label_engine": "mock_evaluator_v2",
    }


def label_single_position(
    engine: chess.engine.SimpleEngine | None,
    fen: str,
    nodes: int = DEFAULT_NODE_BUDGET,
    depth: int | None = None,
    mock: bool = False,
) -> dict[str, Any]:
    board = chess.Board(fen)

    if mock or engine is None:
        return mock_label_position(board)

    limit = chess.engine.Limit(nodes=nodes) if depth is None else chess.engine.Limit(depth=depth)
    info = engine.analyse(board, limit)
    score_obj = info.get("score")

    if score_obj is None:
        return mock_label_position(board)

    pov_score = score_obj.pov(board.turn)

    if pov_score.is_mate():
        mate_moves = pov_score.mate()
        # White perspective mate
        if mate_moves is not None:
            mate_white = mate_moves if board.turn == chess.WHITE else -mate_moves
        else:
            mate_white = None
        clamped_score = CP_CLAMP_MAX if (mate_white and mate_white > 0) else CP_CLAMP_MIN
        return {
            "sf_cp_white": clamped_score,
            "raw_cp": None,
            "is_mate": True,
            "mate_moves": mate_white,
            "sf_nodes": info.get("nodes", nodes),
            "sf_depth": info.get("depth", 0),
            "label_engine": "stockfish",
        }

    raw_cp = pov_score.score()
    if raw_cp is None:
        raw_cp = 0

    # Convert to canonical White perspective
    score_white = raw_cp if board.turn == chess.WHITE else -raw_cp
    clamped_white = max(CP_CLAMP_MIN, min(CP_CLAMP_MAX, score_white))

    return {
        "sf_cp_white": clamped_white,
        "raw_cp": score_white,
        "is_mate": False,
        "mate_moves": None,
        "sf_nodes": info.get("nodes", nodes),
        "sf_depth": info.get("depth", 0),
        "label_engine": "stockfish",
    }


def label_dataset(
    input_file: Path,
    output_file: Path,
    stockfish_path: str | None = None,
    nodes: int = DEFAULT_NODE_BUDGET,
    depth: int | None = None,
    mock: bool = False,
    limit_count: int | None = None,
) -> int:
    sf_exec = find_stockfish_executable(stockfish_path)
    if not mock and not sf_exec:
        raise RuntimeError(
            "Stockfish executable not found! Specify --stockfish-path, set STOCKFISH_PATH, "
            "or run with --mock for development/testing."
        )

    records: list[dict[str, Any]] = []
    with input_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
            if limit_count and len(records) >= limit_count:
                break

    engine: chess.engine.SimpleEngine | None = None
    if not mock and sf_exec:
        engine = chess.engine.SimpleEngine.popen_uci(sf_exec)
        # Configure single-thread for reproducibility
        engine.configure({"Threads": 1, "Hash": 64})

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        labeled_count = 0
        with output_file.open("w", encoding="utf-8") as out:
            for rec in records:
                label_data = label_single_position(
                    engine=engine,
                    fen=rec["fen"],
                    nodes=nodes,
                    depth=depth,
                    mock=mock,
                )
                rec.update(label_data)
                out.write(json.dumps(rec) + "\n")
                labeled_count += 1
                if labeled_count % 200 == 0:
                    print(f"Labeled {labeled_count}/{len(records)} positions...")
        return labeled_count
    finally:
        if engine is not None:
            engine.quit()


def get_default_position_input() -> Path:
    p25 = Path("training/datasets/positions/positions_25k.jsonl")
    if p25.is_file():
        return p25
    p1 = Path("training/datasets/positions/positions_1k.jsonl")
    if p1.is_file():
        return p1
    return p25


def main() -> None:
    parser = argparse.ArgumentParser(description="Label chess positions with Stockfish.")
    parser.add_argument(
        "--input",
        type=Path,
        default=get_default_position_input(),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("training/datasets/labels/labels_25k.jsonl"),
    )
    parser.add_argument("--stockfish-path", type=str, default=None)
    parser.add_argument("--nodes", type=int, default=DEFAULT_NODE_BUDGET)
    parser.add_argument("--depth", type=int, default=None)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    # Automatically enable mock if no Stockfish configured
    sf_exec = find_stockfish_executable(args.stockfish_path)
    use_mock = args.mock or (sf_exec is None)
    if use_mock and not args.mock:
        print("Notice: No Stockfish binary found. Operating in reproducible --mock mode.")

    count = label_dataset(
        input_file=args.input,
        output_file=args.output,
        stockfish_path=sf_exec,
        nodes=args.nodes,
        depth=args.depth,
        mock=use_mock,
        limit_count=args.limit,
    )
    print(f"Successfully labeled {count} positions -> {args.output}")


if __name__ == "__main__":
    main()
