"""Stockfish baseline agent for AI Chessathon sparring and benchmarking.

Never packaged into competition submission; used strictly for local offline
calibration, tournaments, and ACPL evaluations.
"""

from __future__ import annotations

import asyncio
import atexit
import concurrent.futures
import contextlib
import os
import shutil
import sys
import threading
from typing import Any

import chess
import chess.engine

DEFAULT_STOCKFISH_CANDIDATES: list[str] = [
    (
        "C:/Users/Babar/AppData/Local/Microsoft/WinGet/Packages/"
        "Stockfish.Stockfish_Microsoft.Winget.Source_8wekyb3d8bbwe/stockfish/"
        "stockfish-windows-x86-64-avx2.exe"
    ),
    "stockfish",
    "/usr/games/stockfish",
    "/usr/local/bin/stockfish",
]

_ENGINE: chess.engine.SimpleEngine | None = None


def _patch_run_in_background() -> None:
    def run_in_background_daemon(
        coroutine: Any, *, name: str | None = None, debug: bool | None = None
    ) -> Any:
        future: concurrent.futures.Future[Any] = concurrent.futures.Future()

        def background() -> None:
            try:
                asyncio.run(coroutine(future), debug=debug)
                future.cancel()
            except Exception as exc:
                future.set_exception(exc)

        threading.Thread(target=background, name=name, daemon=True).start()
        return future.result()

    chess.engine.run_in_background = run_in_background_daemon


def find_stockfish_binary() -> str | None:
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path:
        resolved = shutil.which(env_path)
        if resolved:
            return resolved
        raise FileNotFoundError(f"Invalid STOCKFISH_PATH: {env_path}")
    for cand in DEFAULT_STOCKFISH_CANDIDATES:
        resolved = shutil.which(cand)
        if resolved:
            return resolved
    return None


def get_stockfish_engine() -> chess.engine.SimpleEngine | None:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    sf_bin = find_stockfish_binary()
    if sf_bin is None:
        raise FileNotFoundError("Stockfish is required for this offline baseline")

    try:
        skill_level = int(os.environ.get("STOCKFISH_SKILL_LEVEL", "5"))
        if not 0 <= skill_level <= 20:
            raise ValueError("STOCKFISH_SKILL_LEVEL must be between 0 and 20")
        threads = int(os.environ.get("STOCKFISH_THREADS", "1"))
        if threads < 1:
            raise ValueError("STOCKFISH_THREADS must be positive")
        # python-chess normally creates a non-daemon event-loop thread, which
        # would prevent atexit from closing this persistent offline engine.
        original_background = chess.engine.run_in_background
        _patch_run_in_background()
        try:
            engine = chess.engine.SimpleEngine.popen_uci(sf_bin)
        finally:
            chess.engine.run_in_background = original_background
        try:
            engine.configure({"Skill Level": skill_level, "Threads": threads, "Hash": 16})
        except Exception:
            engine.close()
            raise
        _ENGINE = engine
        return _ENGINE
    except Exception as e:
        print(f"[WARN] Failed to start Stockfish baseline: {e}", file=sys.stderr)
        raise


def close_stockfish_engine() -> None:
    global _ENGINE
    if _ENGINE is not None:
        with contextlib.suppress(Exception):
            _ENGINE.close()
        _ENGINE = None


def get_move(fen: str, time_left_ms: int) -> str:
    """Choose move using calibrated Stockfish baseline."""
    board = chess.Board(fen)
    engine = get_stockfish_engine()

    if engine is not None:
        # Determine time limit per move
        fixed_time_ms = os.environ.get("STOCKFISH_TIME_PER_MOVE_MS")
        if fixed_time_ms:
            time_limit_s = max(0.01, float(fixed_time_ms) / 1000.0)
        else:
            time_limit_s = max(0.05, min(1.0, (time_left_ms / 1000.0) * 0.05))
        time_limit_s = min(time_limit_s, max(0.001, time_left_ms / 2000.0))

        try:
            result = engine.play(board, chess.engine.Limit(time=time_limit_s))
            if result.move is not None and result.move in board.legal_moves:
                return result.move.uci()
        except Exception as e:
            print(f"[WARN] Stockfish move query failed: {e}", file=sys.stderr)

    raise RuntimeError("Stockfish failed to return a legal move")


atexit.register(close_stockfish_engine)

# The official runner imports this module as 'agent'; initialization belongs
# in its import budget. Tool imports can still discover the binary lazily.
if __name__ == "agent":
    get_stockfish_engine()
