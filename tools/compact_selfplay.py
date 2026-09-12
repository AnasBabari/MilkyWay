"""Generate outcome-learning games with isolated sides and the unchanged referee."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, cast

import chess
import chess.engine

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.referee import FAILED_TERMINATIONS, play_match  # noqa: E402
from harness.sandbox import local  # noqa: E402
from tools.candidate_screen import atomic_save_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--games", type=int, default=16)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--stockfish-level", type=int, choices=range(21))
    parser.add_argument("--base-ms", type=int, default=10000)
    parser.add_argument("--increment-ms", type=int, default=100)
    parser.add_argument("--openings", type=Path)
    args = parser.parse_args()
    openings = None
    if args.openings is not None:
        openings = json.loads(args.openings.read_text())["positions"]
        assert len(openings) >= (args.games if args.stockfish_level is None else args.games // 2)
    opponent = args.agent
    stockfish_spec = None
    if args.stockfish_level is not None:
        from baselines.stockfish.agent import (
            close_stockfish_engine,
            find_stockfish_binary,
            get_stockfish_engine,
        )

        assert args.games % 2 == 0, "Stronger-opponent training uses complete colour pairs"
        os.environ["STOCKFISH_SKILL_LEVEL"] = str(args.stockfish_level)
        os.environ["STOCKFISH_THREADS"] = "1"
        os.environ.pop("STOCKFISH_TIME_PER_MOVE_MS", None)
        binary = find_stockfish_binary()
        assert binary
        engine = get_stockfish_engine()
        assert engine is not None
        assert (
            cast(chess.engine.UciProtocol, engine.protocol).config["Skill Level"]
            == args.stockfish_level
        )
        close_stockfish_engine()
        opponent = ROOT / "baselines/stockfish"
        stockfish_spec = {
            "level": args.stockfish_level,
            "threads": 1,
            "hash": 16,
            "binary_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
            "adapter_sha256": hashlib.sha256((opponent / "agent.py").read_bytes()).hexdigest(),
            "budget": "unchanged clock-fraction adapter; no fixed-movetime override",
        }
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "agent": str(args.agent.resolve()),
        "seed": args.seed,
        "base_ms": args.base_ms,
        "increment_ms": args.increment_ms,
        "source_hashes": {
            str(p.relative_to(args.agent)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in args.agent.rglob("*")
            if p.is_file() and p.suffix in (".py", ".onnx", ".npz")
        },
        "harness_hashes": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "harness").glob("*.py")
        },
    }
    if stockfish_spec is not None:
        manifest["stockfish"] = stockfish_spec
        manifest["generator_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        manifest["purpose"] = "training curriculum only; not a promotion tournament"
    if args.openings is not None:
        manifest["opening_pool_sha256"] = hashlib.sha256(args.openings.read_bytes()).hexdigest()
    path = args.out / "manifest.json"
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise SystemExit("Source changed: use a new self-play directory")
    atomic_save_json(path, manifest)
    lock = args.out / "writer.lock"
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))

    def play(index: int) -> dict[str, Any]:
        opening_index = index if stockfish_spec is None else index // 2
        rng = random.Random(args.seed + opening_index)
        if openings is not None:
            board = chess.Board(openings[opening_index]["fen"])
        else:
            board = chess.Board()
            for _ in range(8):
                board.push(rng.choice(list(board.legal_moves)))
                if board.is_game_over():
                    board = chess.Board()
        white, black = (args.agent, opponent) if index % 2 == 0 else (opponent, args.agent)
        outcome = play_match(
            local(white, index * 2),
            local(black, index * 2 + 1),
            args.base_ms,
            args.increment_ms,
            start_fen=board.fen(),
        )
        if outcome.termination in FAILED_TERMINATIONS or outcome.result == "void":
            raise RuntimeError(f"Self-play reliability failure: {outcome.termination}")
        return {
            "game_id": index,
            "seed": args.seed + opening_index,
            "start_fen": board.fen(),
            "result": outcome.result,
            "termination": outcome.termination,
            "pgn": outcome.pgn,
            "candidate_color": "white" if index % 2 == 0 else "black",
            "split": "val" if opening_index % 5 == 0 else "train",
        }

    try:
        pending = [i for i in range(args.games) if not (args.out / f"game_{i:05d}.json").exists()]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(play, i) for i in pending]
            for future in concurrent.futures.as_completed(futures):
                record = future.result()
                atomic_save_json(args.out / f"game_{record['game_id']:05d}.json", record)
                print(
                    f"game={record['game_id']} result={record['result']} "
                    f"termination={record['termination']}",
                    flush=True,
                )
    finally:
        lock.unlink()


if __name__ == "__main__":
    main()
