# ruff: noqa: E402
"""Stockfish tournament benchmark and calibration runner for MilkyWay.

Runs paired opening matches against calibrated Stockfish levels (e.g., Level 3, 5, 8)
on level-checked opening banks (screen_bank, confirm_bank), reporting score,
paired confidence intervals, termination reasons, and in-game ACPL.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import chess.engine
import chess.pgn

from baselines.stockfish.agent import find_stockfish_binary
from harness.referee import play_match
from harness.sandbox import local
from tools.m18_tournament import PairRecord, analyze_stage_results
from tools.measure_acpl import measure_move_loss
from tools.test_bank import BankPosition


def atomic_save_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(f".tmp_{os.getpid()}_{random.randint(1000, 9999)}")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def compute_game_acpl(
    pgn_text: str,
    engine: chess.engine.SimpleEngine,
    agent_color: chess.Color,
    eval_time_s: float = 0.05,
    cpl_cap: float = 1000.0,
) -> tuple[float, list[float]]:
    """Compute ACPL for the agent's moves in a completed game PGN."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None or game.errors:
        raise ValueError("Invalid PGN for ACPL evaluation")
    board = game.board()
    losses: list[float] = []
    for move in game.mainline_moves():
        if board.turn == agent_color:
            losses.append(
                float(measure_move_loss(engine, board, move, eval_time_s, cpl_cap)["cpl"])
            )
        board.push(move)
    return (sum(losses) / len(losses) if losses else 0.0), losses


def run_benchmark_level(
    agent_path: Path,
    level: int,
    positions: list[BankPosition],
    n_pairs: int,
    base_ms: int,
    increment_ms: int,
    workers: int,
    out_dir: Path,
    compute_acpl: bool = True,
) -> dict[str, Any]:
    """Run a calibrated benchmark match series against a specific Stockfish level."""
    if not 0 <= level <= 20 or not 1 <= n_pairs <= len(positions):
        raise ValueError("Invalid skill level or pair count")
    if workers < 1 or base_ms <= 0 or increment_ms < 0:
        raise ValueError("Invalid worker count or time control")
    sf_path = find_stockfish_binary()
    if sf_path is None:
        raise FileNotFoundError("Stockfish binary not found")
    sf_opponent_dir = ROOT / "baselines" / "stockfish"
    level_dir = out_dir / f"level_{level}"
    level_dir.mkdir(parents=True, exist_ok=True)

    os.environ["STOCKFISH_SKILL_LEVEL"] = str(level)

    manifest = {
        "level": level,
        "base_ms": base_ms,
        "increment_ms": increment_ms,
        "stockfish_path": sf_path,
        "stockfish_sha256": hashlib.sha256(Path(sf_path).read_bytes()).hexdigest(),
        "stockfish_time_per_move_ms": os.environ.get("STOCKFISH_TIME_PER_MOVE_MS"),
        "stockfish_threads": os.environ.get("STOCKFISH_THREADS", "1"),
        "opponent_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(sf_opponent_dir.glob("*.py"))
        },
        "harness_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "harness").glob("*.py"))
        },
        "agent_sha256": {
            str(p.relative_to(agent_path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted([*agent_path.glob("*.py"), *agent_path.glob("weights/*")])
            if p.is_file()
        },
        "positions": [(p.id, p.fen) for p in positions[:n_pairs]],
        "acpl_method_version": 3,
    }
    manifest = json.loads(json.dumps(manifest))
    manifest_path = level_dir / "manifest.json"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text()) != manifest:
            raise ValueError("Benchmark configuration changed; use a fresh output directory")
    elif (level_dir / "pairs.json").exists():
        raise ValueError("Existing results lack a manifest; use a fresh output directory")
    atomic_save_json(manifest_path, manifest)
    pairs_file = level_dir / "pairs.json"
    games_dir = level_dir / "paired_games"
    games_dir.mkdir(exist_ok=True)
    saved = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(games_dir.glob("*.json"))]
    results = [PairRecord(**item["record"]) for item in saved]
    completed_ids = {r.pos_id for r in results}
    pending = [p for p in positions[:n_pairs] if p.id not in completed_ids]

    pgn_file = level_dir / "games.pgn"

    print("=======================================================")
    print(f"Starting Stockfish Benchmark — Skill Level {level}")
    print(f"Pairs: {n_pairs} (2 games per pair = {n_pairs * 2} games)")
    print(f"Base: {base_ms}ms, Inc: {increment_ms}ms, Workers: {workers}")
    print("=======================================================")

    def play_and_record(pos: BankPosition) -> tuple[PairRecord, str, str]:
        out_w = play_match(
            local(agent_path),
            local(sf_opponent_dir),
            base_ms,
            increment_ms,
            start_fen=pos.fen,
        )
        if out_w.result == "void":
            raise RuntimeError("Both agents failed in white game")
        if out_w.result == "draw":
            w_score = 0.5
        elif out_w.result == "white":
            w_score = 1.0
        else:
            w_score = 0.0

        out_b = play_match(
            local(sf_opponent_dir),
            local(agent_path),
            base_ms,
            increment_ms,
            start_fen=pos.fen,
        )
        if out_b.result == "void":
            raise RuntimeError("Both agents failed in black game")
        if out_b.result == "draw":
            b_score = 0.5
        elif out_b.result == "black":
            b_score = 1.0
        else:
            b_score = 0.0

        rec = PairRecord(
            pos_id=pos.id,
            category=pos.category,
            start_fen=pos.fen,
            starting_ply=chess.Board(pos.fen).ply(),
            white_result=out_w.result,
            white_term=out_w.termination,
            white_score=w_score,
            black_result=out_b.result,
            black_term=out_b.termination,
            black_score=b_score,
            pair_score=w_score + b_score,
        )
        return rec, out_w.pgn, out_b.pgn

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(play_and_record, pos): pos for pos in pending}
        for fut in concurrent.futures.as_completed(futures):
            rec, pgn_w, pgn_b = fut.result()
            item = {"record": rec.to_dict(), "white_pgn": pgn_w, "black_pgn": pgn_b}
            pair_name = hashlib.sha256(rec.pos_id.encode()).hexdigest()[:16]
            atomic_save_json(games_dir / f"{pair_name}.json", item)
            saved.append(item)
            results.append(rec)
            results.sort(key=lambda r: r.pos_id)
            atomic_save_json(pairs_file, [r.to_dict() for r in results])

            print(
                f"[{len(results)}/{n_pairs}] Pair {rec.pos_id}: {rec.pair_score}/2 "
                f"(White: {rec.white_result}, Black: {rec.black_result})",
                flush=True,
            )

    with pgn_file.open("w", encoding="utf-8") as pf:
        for item in sorted(saved, key=lambda item: item["record"]["pos_id"]):
            pf.write(item["white_pgn"] + "\n\n" + item["black_pgn"] + "\n\n")
    atomic_save_json(pairs_file, [r.to_dict() for r in results])
    report = analyze_stage_results(results)
    report["stockfish_level"] = level
    atomic_save_json(level_dir / "report.json", report)

    acpl_data: dict[str, Any] = {}
    if compute_acpl and pgn_file.exists():
        print("Computing full-strength oracle ACPL for all saved games...", flush=True)
        game_details: list[dict[str, Any]] = []
        all_cpls: list[float] = []
        with chess.engine.SimpleEngine.popen_uci(sf_path) as oracle:
            oracle.configure(
                {"Threads": 1, "Hash": 32, "Skill Level": 20, "UCI_LimitStrength": False}
            )
            with pgn_file.open(encoding="utf-8") as source:
                index = 0
                while (game := chess.pgn.read_game(source)) is not None:
                    color = chess.WHITE if index % 2 == 0 else chess.BLACK
                    mean, losses = compute_game_acpl(str(game), oracle, color)
                    game_details.append(
                        {
                            "game_index": index,
                            "agent_color": color,
                            "mean_acpl": mean,
                            "move_cpl": losses,
                        }
                    )
                    all_cpls.extend(losses)
                    index += 1
            if index != 2 * len(results):
                raise ValueError("PGN/result count mismatch; use a fresh output directory")
        acpl_data = {
            "mean_acpl": sum(all_cpls) / len(all_cpls) if all_cpls else None,
            "total_moves_evaluated": len(all_cpls),
            "oracle_skill_level": 20,
            "score_cap_cp": 1000,
            "games": game_details,
        }
        atomic_save_json(level_dir / "acpl.json", acpl_data)
    report["acpl"] = acpl_data
    atomic_save_json(level_dir / "report.json", report)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, default=Path("."))
    parser.add_argument(
        "--level",
        type=int,
        default=5,
        help="Stockfish Skill Level (0-20, default 5)",
    )
    parser.add_argument(
        "--levels",
        type=str,
        default=None,
        help="Comma-separated list of skill levels to test sequentially (e.g., '3,5,8')",
    )
    parser.add_argument(
        "--bank",
        choices=["screen", "confirm", "dev"],
        default="screen",
    )
    parser.add_argument("--pairs", type=int, default=10)
    parser.add_argument("--base-ms", type=int, default=5000)
    parser.add_argument("--increment-ms", type=int, default=100)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("experiments/r34/stockfish_benchmark"),
    )
    parser.add_argument("--no-acpl", action="store_true", help="Skip ACPL post-processing")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    if args.bank == "screen":
        from tools.screen_bank import SCREEN_TEST_BANK

        positions = list(SCREEN_TEST_BANK)
    elif args.bank == "confirm":
        from tools.confirm_bank import CONFIRM_TEST_BANK

        positions = list(CONFIRM_TEST_BANK)
    else:
        from tools.test_bank import PAIRED_TEST_BANK

        positions = list(PAIRED_TEST_BANK)

    rng = random.Random(args.seed)
    rng.shuffle(positions)

    levels = [int(x.strip()) for x in args.levels.split(",")] if args.levels else [args.level]

    overall_results: dict[str, Any] = {}
    for lvl in levels:
        lvl_report = run_benchmark_level(
            agent_path=args.agent,
            level=lvl,
            positions=positions,
            n_pairs=args.pairs,
            base_ms=args.base_ms,
            increment_ms=args.increment_ms,
            workers=args.workers,
            out_dir=args.out,
            compute_acpl=not args.no_acpl,
        )
        overall_results[f"level_{lvl}"] = lvl_report

    summary_file = args.out / "benchmark_summary.json"
    atomic_save_json(summary_file, overall_results)
    print("\n=======================================================")
    print(f"Stockfish Benchmark Complete. Summary saved to {summary_file}")
    print("=======================================================")


if __name__ == "__main__":
    main()
