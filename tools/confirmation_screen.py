"""Independent full-clock confirmation runner; never promotes or uploads."""

from __future__ import annotations

import argparse
import atexit
import concurrent.futures
import functools
import hashlib
import json
import os
import platform
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.m18_tournament import (  # noqa: E402
    PairRecord,
    analyze_stage_results,
    load_pairs,
    play_single_pair,
)
from tools.test_bank import BankPosition  # noqa: E402


def atomic_save_json(path: Path, data: Any) -> None:
    """Atomically write JSON data using temp file and replace."""
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


def atomic_save_pairs(path: Path, pairs: list[PairRecord]) -> None:
    """Atomically write pair records."""
    data = [p.to_dict() for p in pairs]
    atomic_save_json(path, data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bank-json", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=50)
    parser.add_argument("--base-ms", type=int, default=120000)
    parser.add_argument("--increment-ms", type=int, default=500)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seed", type=int, default=2026090822)
    parser.add_argument("--record-games", action="store_true",
                        help="Retain referee PGNs and reject void games; use a new run directory")
    parser.add_argument(
        "--stockfish-level",
        type=int,
        default=5,
        help="Stockfish skill level (0-20) when playing against baselines/stockfish",
    )
    args = parser.parse_args()
    if not 0 <= args.stockfish_level <= 20:
        parser.error("--stockfish-level must be between 0 and 20")

    os.environ["STOCKFISH_SKILL_LEVEL"] = str(args.stockfish_level)

    # Do not inherit accidental tuning overrides from the invoking shell.
    overrides = {k: v for k, v in os.environ.items() if k.startswith("MILKYWAY_")}
    if overrides:
        raise SystemExit(f"Remove engine environment overrides first: {sorted(overrides)}")
    args.out.mkdir(parents=True, exist_ok=True)

    if (args.pairs, args.base_ms, args.increment_ms, args.workers) != (50, 120000, 500, 1):
        raise SystemExit("Confirmation requires50pairs,120s+0.5s,and1worker")
    if not args.record_games:
        raise SystemExit("Confirmation requires --record-games")
    if (args.out / "futility_decision.json").exists():
        raise SystemExit("Never resume a stopped confirmation")
    bank = json.loads(args.bank_json.read_text())
    if bank.get("status") != "frozen independent bank":
        raise SystemExit("Bank must pass its final independent overlap audit first")
    positions = [BankPosition(p["id"], "opening", p["fen"], 1) for p in bank["positions"]]
    if len(positions) != 50 or len({p.id for p in positions}) != 50:
        raise SystemExit("Expected exactly50unique paired positions")
    random.Random(args.seed).shuffle(positions)
    bank_file = str(args.bank_json.resolve().relative_to(ROOT)).replace("\\", "/")
    args.bank = "fresh_independent_confirmation"
    evidence_type = "Frozen fresh bank,120s+0.5s,100games; gates assessed after completion"

    if not 1 <= args.pairs <= len(positions):
        raise SystemExit(f"pairs must be between 1 and {len(positions)}")

    def hashes(directory: Path) -> dict[str, str]:
        files = list(directory.glob("*.py")) + [
            p for p in (directory / "weights").rglob("*") if p.is_file()
        ]
        return {
            str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files)
        }

    manifest = {
        "agent": str(args.agent.resolve()),
        "opponent": str(args.opponent.resolve()),
        "agent_sha256": hashes(args.agent),
        "opponent_sha256": hashes(args.opponent),
        "base_ms": args.base_ms,
        "increment_ms": args.increment_ms,
        "bank": args.bank,
        "seed": args.seed,
        "workers": args.workers,
        "stockfish_level": args.stockfish_level,
        "python": platform.python_version(),
        "positions": [{"id": p.id, "fen": p.fen} for p in positions],
        "evidence_type": evidence_type,
        "harness_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "harness/referee.py",
                "harness/rules.py",
                "harness/runner.py",
                bank_file,
            )
        },
    }
    manifest_path = args.out / "manifest.json"
    pair_player = play_single_pair
    if args.record_games:
        from tools.recorded_pair import play_recorded_pair

        manifest["recorded_games"] = True
        manifest["orchestration_sha256"] = {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("tools/confirmation_screen.py", "tools/recorded_pair.py",
                         "tools/m18_tournament.py", "harness/sandbox.py")
        }
        pair_player = functools.partial(play_recorded_pair, out=args.out / "games")
    if args.opponent.resolve() == (ROOT / "baselines/stockfish").resolve():
        from baselines.stockfish.agent import find_stockfish_binary

        binary = find_stockfish_binary()
        if binary is None:
            raise SystemExit("Stockfish binary not found")
        manifest["stockfish"] = {
            "path": binary,
            "sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
            "skill_level": args.stockfish_level,
            "threads": os.environ.get("STOCKFISH_THREADS", "1"),
            "time_per_move_ms": os.environ.get("STOCKFISH_TIME_PER_MOVE_MS"),
        }
    if manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cmp_existing = {k: v for k, v in existing_manifest.items() if k != "workers"}
        cmp_new = {k: v for k, v in manifest.items() if k != "workers"}
        if cmp_existing != cmp_new:
            raise SystemExit("Manifest changed; use a fresh output directory")
    if args.record_games:
        lock = args.out / "writer.lock"
        with lock.open("x") as stream:
            stream.write(str(os.getpid()))
        atexit.register(lock.unlink, missing_ok=True)
    atomic_save_json(manifest_path, manifest)

    result_path = args.out / "pairs.json"
    results = load_pairs(result_path) if result_path.exists() else []
    completed = {r.pos_id for r in results}
    pending = [p for p in positions[: args.pairs] if p.id not in completed]

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                pair_player,
                args.agent,
                args.opponent,
                p,
                args.base_ms,
                args.increment_ms,
            )
            for p in pending
        ]
        for future in concurrent.futures.as_completed(futures):
            rec = future.result()
            results.append(rec)
            results.sort(key=lambda r: r.pos_id)
            atomic_save_pairs(result_path, results)
            print(
                f"{len(results)}/{args.pairs} {rec.pos_id}: {rec.pair_score}/2 "
                f"{rec.white_term}/{rec.black_term}",
                flush=True,
            )

    report = analyze_stage_results(results)
    atomic_save_json(args.out / f"report_{len(results) * 2}.json", report)
    print(json.dumps(report, indent=2), flush=True)
    if report["failed_terminations"]:
        raise SystemExit("Reliability failures: candidate cannot qualify")


if __name__ == "__main__":
    main()
