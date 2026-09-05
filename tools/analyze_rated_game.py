"""PGN forensic analyzer for rated MilkyWay games.

Reconstructs positions faced by MilkyWay in tournament games and evaluates:
1. Root policy distributions, ranks, probabilities, and entropy.
2. Current MilkyWay search telemetry (depth, seldepth, nodes, qnodes, NPS, PV).
3. Frozen MW-0.2 counterfactual decisions (in an isolated worker process).
4. Offline Stockfish multi-PV evaluations, CPL, and WDL deltas.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess  # noqa: E402
import chess.engine  # noqa: E402
import chess.pgn  # noqa: E402
import numpy as np  # noqa: E402

from engine import MilkyWayEngine  # noqa: E402
from root_policy import get_root_evaluator  # noqa: E402

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


@dataclass
class PolicyTelemetry:
    played_rank: int | None = None
    played_prob: float | None = None
    best_policy_move: str | None = None
    best_policy_san: str | None = None
    policy_entropy: float | None = None
    top_moves: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SearchTelemetry:
    selected_move: str | None = None
    score: int | None = None
    depth: int = 0
    seldepth: int = 0
    nodes: int = 0
    qnodes: int = 0
    nps: int = 0
    pv: list[str] = field(default_factory=list)


@dataclass
class MW02Telemetry:
    selected_move: str | None = None
    score: int | None = None
    depth: int = 0
    seldepth: int = 0
    pv: list[str] = field(default_factory=list)


@dataclass
class StockfishTelemetry:
    best_move: str | None = None
    best_san: str | None = None
    top_5: list[dict[str, Any]] = field(default_factory=list)
    cp_before: int | None = None
    cp_after: int | None = None
    wdl_before: dict[str, int] | None = None
    wdl_after: dict[str, int] | None = None
    cpl: int | None = None
    is_mate: bool = False
    mate_in: int | None = None


@dataclass
class MoveForensicRecord:
    move_number: int
    ply: int
    fen: str
    played_move: str
    played_san: str
    time_used_s: float
    clock_remaining_s: float
    policy: PolicyTelemetry
    milkyway_search: SearchTelemetry
    mw02: MW02Telemetry
    stockfish: StockfishTelemetry


class MW02IsolatedRunner:
    """Isolated subprocess runner for MW-0.2 to prevent sys.modules pollution."""

    def __init__(self, mw02_dir: Path) -> None:
        self.mw02_dir = mw02_dir.resolve()
        self.process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        if not self.mw02_dir.exists():
            return
        worker_code = """
import sys, json
from pathlib import Path
v_dir = Path(".").resolve()
sys.path.insert(0, str(v_dir))
import engine
eng = engine.MilkyWayEngine()

while True:
    line = sys.stdin.readline()
    if not line:
        break
    data = json.loads(line)
    fen = data["fen"]
    clock_ms = data["clock_ms"]
    m = eng.choose_move(fen, clock_ms)
    stats = eng.searcher.stats
    resp = {
        "move": m,
        "score": stats.score,
        "depth": stats.depth_reached,
        "seldepth": stats.seldepth,
        "pv": stats.pv,
    }
    sys.stdout.write(json.dumps(resp) + "\\n")
    sys.stdout.flush()
"""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.mw02_dir)
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-u", "-c", worker_code],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.mw02_dir),
                text=True,
                bufsize=1,
                env=env,
            )
        except Exception as e:
            print(f"[WARN] Failed to spawn MW-0.2 isolated worker: {e}", file=sys.stderr)
            self.process = None

    def query(self, fen: str, clock_ms: int) -> MW02Telemetry:
        if self.process is None or self.process.poll() is not None:
            return MW02Telemetry()
        if self.process.stdin is None or self.process.stdout is None:
            return MW02Telemetry()
        req = json.dumps({"fen": fen, "clock_ms": clock_ms})
        try:
            self.process.stdin.write(req + "\n")
            self.process.stdin.flush()
            line = self.process.stdout.readline()
            if not line:
                return MW02Telemetry()
            resp = json.loads(line)
            return MW02Telemetry(
                selected_move=resp.get("move"),
                score=resp.get("score"),
                depth=resp.get("depth", 0),
                seldepth=resp.get("seldepth", 0),
                pv=resp.get("pv", []),
            )
        except Exception:
            return MW02Telemetry()

    def close(self) -> None:
        if self.process is not None:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                pass
            self.process = None


def compute_policy_telemetry(board: chess.Board, played_uci: str) -> PolicyTelemetry:
    """Computes root policy telemetry including distribution entropy and ranks."""
    evaluator = get_root_evaluator()
    legal_moves = list(board.legal_moves)
    if not evaluator.is_available() or not legal_moves:
        return PolicyTelemetry()

    raw_scores = evaluator.get_move_scores(board, legal_moves)
    moves = list(raw_scores.keys())
    logits = np.array([raw_scores[m] for m in moves], dtype=np.float32)
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    probs = exp / np.sum(exp)
    entropy = float(-np.sum(probs * np.log(probs + 1e-12)))

    ranked_indices = np.argsort(-probs)
    sorted_moves = [moves[i] for i in ranked_indices]
    sorted_probs = [float(probs[i]) for i in ranked_indices]
    sorted_logits = [float(logits[i]) for i in ranked_indices]

    move_to_rank = {m.uci(): r + 1 for r, m in enumerate(sorted_moves)}
    move_to_prob = {m.uci(): round(p, 5) for m, p in zip(sorted_moves, sorted_probs, strict=True)}

    best_m = sorted_moves[0]
    top_5 = [
        {
            "rank": r + 1,
            "uci": m.uci(),
            "san": board.san(m),
            "prob": round(p, 4),
            "logit": round(logit_val, 3),
        }
        for r, (m, p, logit_val) in enumerate(
            zip(sorted_moves[:5], sorted_probs[:5], sorted_logits[:5], strict=False)
        )
    ]

    return PolicyTelemetry(
        played_rank=move_to_rank.get(played_uci),
        played_prob=move_to_prob.get(played_uci),
        best_policy_move=best_m.uci(),
        best_policy_san=board.san(best_m),
        policy_entropy=round(entropy, 4),
        top_moves=top_5,
    )


def query_milkyway_search(
    engine: MilkyWayEngine, fen: str, clock_ms: int
) -> SearchTelemetry:
    """Runs a search on the current MilkyWay engine and captures full telemetry."""
    t0 = time.monotonic()
    move = engine.choose_move(fen, clock_ms)
    elapsed = max(0.001, time.monotonic() - t0)
    stats = engine.searcher.stats
    total_nodes = stats.nodes + stats.qnodes
    nps = int(total_nodes / elapsed)
    return SearchTelemetry(
        selected_move=move,
        score=stats.score,
        depth=stats.depth_reached,
        seldepth=stats.seldepth,
        nodes=stats.nodes,
        qnodes=stats.qnodes,
        nps=nps,
        pv=stats.pv,
    )


def score_to_cp(score_obj: chess.engine.PovScore | None) -> tuple[int | None, bool, int | None]:
    if score_obj is None:
        return None, False, None
    white_score = score_obj.white()
    if white_score.is_mate():
        m = white_score.mate()
        cp = 30000 if (m and m > 0) else -30000
        return cp, True, m
    return white_score.score(), False, None


def wdl_to_dict(wdl_obj: chess.engine.PovWdl | None) -> dict[str, int] | None:
    if wdl_obj is None:
        return None
    w = wdl_obj.white()
    return {"win": w.wins, "draw": w.draws, "loss": w.losses}


def query_stockfish(
    sf_engine: chess.engine.SimpleEngine | None,
    board: chess.Board,
    played_uci: str,
    nodes: int = 100000,
) -> StockfishTelemetry:
    """Runs Stockfish multi-PV 5 analysis before and single PV after the played move."""
    if sf_engine is None:
        return StockfishTelemetry()
    try:
        info_list = sf_engine.analyse(board, chess.engine.Limit(nodes=nodes), multipv=5)
        top_5: list[dict[str, Any]] = []
        best_uci: str | None = None
        best_san: str | None = None
        best_cp: int | None = None
        best_mate: int | None = None
        best_wdl: dict[str, int] | None = None

        for entry in info_list:
            pv = entry.get("pv", [])
            m = pv[0] if pv else None
            score_obj = entry.get("score")
            cp, _is_mate, mate_val = score_to_cp(score_obj)
            wdl = wdl_to_dict(entry.get("wdl"))

            if entry.get("multipv") == 1 and m:
                best_uci = m.uci()
                best_san = board.san(m)
                best_cp = cp
                best_mate = mate_val
                best_wdl = wdl

            top_5.append({
                "multipv": entry.get("multipv"),
                "move_uci": m.uci() if m else None,
                "move_san": board.san(m) if m else None,
                "score_cp": cp,
                "mate_in": mate_val,
                "wdl": wdl,
                "pv": [x.uci() for x in pv[:6]],
            })

        # Score after played move
        played_m = chess.Move.from_uci(played_uci)
        board.push(played_m)
        info_after = sf_engine.analyse(board, chess.engine.Limit(nodes=nodes), multipv=1)
        board.pop()

        entry_after = info_after[0] if isinstance(info_after, list) else info_after
        cp_after, _, _mate_after = score_to_cp(entry_after.get("score"))
        wdl_after = wdl_to_dict(entry_after.get("wdl"))

        cpl = 0
        if (
            best_cp is not None
            and cp_after is not None
            and abs(best_cp) < 20000
            and abs(cp_after) < 20000
        ):
            cpl = max(0, best_cp - cp_after)

        return StockfishTelemetry(
            best_move=best_uci,
            best_san=best_san,
            top_5=top_5,
            cp_before=best_cp,
            cp_after=cp_after,
            wdl_before=best_wdl,
            wdl_after=wdl_after,
            cpl=cpl,
            is_mate=(best_mate is not None),
            mate_in=best_mate,
        )
    except Exception as e:
        print(f"[WARN] Stockfish evaluation failed: {e}", file=sys.stderr)
        return StockfishTelemetry()


def parse_positions_from_pgn(
    pgn_path: Path, log_path: Path | None = None, color_str: str = "white"
) -> list[dict[str, Any]]:
    """Reconstructs every position faced by MilkyWay from a PGN and optional platform log."""
    with open(pgn_path, encoding="utf-8") as f:
        game = chess.pgn.read_game(f)
    if game is None:
        raise ValueError(f"Could not parse PGN from {pgn_path}")

    target_color = chess.WHITE if color_str.lower() == "white" else chess.BLACK

    # Parse platform log if available
    timing_data: list[tuple[float, float, float]] = []
    if log_path and log_path.exists():
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("{") and "clock_before_s" in line:
                    try:
                        d = json.loads(line)
                        timing_data.append((
                            float(d.get("time_used_s", 0.0)),
                            float(d.get("clock_before_s", 120.0)),
                            float(d.get("clock_after_s", 120.0)),
                        ))
                    except Exception:
                        pass
                else:
                    pat = r"time(?:\s+used)?:?\s*([\d\.]+)s?.*clock:?\s*([\d\.]+)s?"
                    pat_match = re.search(pat, line, re.I)
                    if pat_match:
                        used = float(pat_match.group(1))
                        remaining = float(pat_match.group(2))
                        timing_data.append((used, remaining + used, remaining))

    board = game.board()
    positions: list[dict[str, Any]] = []
    move_count = 0

    clock = 120.0
    for node in game.mainline():
        is_our_turn = (board.turn == target_color)
        m = node.move
        if is_our_turn:
            move_count += 1
            fen = board.fen()
            san = board.san(m)
            uci = m.uci()

            comment = node.comment
            clk_match = re.search(r"%clk\s+(\d+):(\d+):([\d\.]+)", comment)

            time_used = 1.0
            clock_before = clock
            if clk_match:
                hours = int(clk_match.group(1))
                minutes = int(clk_match.group(2))
                seconds = float(clk_match.group(3))
                clock_after = hours * 3600 + minutes * 60 + seconds
                time_used = max(0.0, clock_before - clock_after + 0.5)
                clock = clock_after
            elif timing_data and (move_count - 1) < len(timing_data):
                time_used, clock_before, clock_after = timing_data[move_count - 1]
                clock = clock_after
            else:
                clock_after = max(0.0, clock_before - time_used + 0.5)
                clock = clock_after

            positions.append({
                "move_number": move_count,
                "ply": board.ply(),
                "fen": fen,
                "played_uci": uci,
                "played_san": san,
                "time_used_s": round(time_used, 1),
                "clock_before_s": round(clock_before, 1),
                "clock_after_s": round(clock_after, 1),
            })
        board.push(m)

    return positions


def find_stockfish_binary(candidate_arg: str | None) -> str | None:
    if candidate_arg and Path(candidate_arg).exists():
        return candidate_arg
    env_sf = os.environ.get("STOCKFISH_PATH")
    if env_sf and Path(env_sf).exists():
        return env_sf
    for c in DEFAULT_STOCKFISH_CANDIDATES:
        if Path(c).exists():
            return c
    return None


def format_report_block(rec: MoveForensicRecord) -> str:
    lines = [
        "=" * 80,
        f"Ply: {rec.ply} | Move {rec.move_number}",
        f"FEN: {rec.fen}",
        "",
        f"played move: {rec.played_san} ({rec.played_move})",
        f"time used: {rec.time_used_s:.1f}s",
        f"clock remaining: {rec.clock_remaining_s:.1f}s",
        "",
        "policy:",
        f"    played move rank: {rec.policy.played_rank}",
        f"    played move probability: {rec.policy.played_prob}",
        f"    best policy move: {rec.policy.best_policy_san} ({rec.policy.best_policy_move})",
        f"    policy entropy: {rec.policy.policy_entropy}",
        "    top 5 moves:",
    ]
    for tm in rec.policy.top_moves:
        p_val = tm["prob"]
        l_val = tm["logit"]
        lines.append(
            f"        {tm['rank']}. {tm['san']} ({tm['uci']}): "
            f"p={p_val:.4f}, logit={l_val:.2f}"
        )

    mate_str = f"Mate in {rec.stockfish.mate_in}" if rec.stockfish.is_mate else "None"
    lines.extend([
        "",
        "MilkyWay search:",
        f"    selected move: {rec.milkyway_search.selected_move}",
        f"    score: {rec.milkyway_search.score} cp",
        f"    depth: {rec.milkyway_search.depth}",
        f"    seldepth: {rec.milkyway_search.seldepth}",
        f"    nodes: {rec.milkyway_search.nodes}",
        f"    qnodes: {rec.milkyway_search.qnodes}",
        f"    NPS: {rec.milkyway_search.nps}",
        f"    PV: {' '.join(rec.milkyway_search.pv[:6])}",
        "",
        "MW-0.2:",
        f"    selected move: {rec.mw02.selected_move}",
        f"    score: {rec.mw02.score} cp",
        f"    PV: {' '.join(rec.mw02.pv[:6])}",
        "",
        "Stockfish offline:",
        f"    best move: {rec.stockfish.best_san} ({rec.stockfish.best_move})",
        "    top 5:",
    ])
    for entry in rec.stockfish.top_5:
        san = entry.get("move_san")
        cp = entry.get("score_cp")
        mate = entry.get("mate_in")
        score_str = f"M{mate}" if mate else f"{cp} cp"
        wdl = entry.get("wdl")
        wdl_str = f"({wdl['win']}/{wdl['draw']}/{wdl['loss']})" if wdl else ""
        lines.append(f"        {entry.get('multipv')}. {san}: {score_str} {wdl_str}")

    lines.extend([
        f"    played-move cp: {rec.stockfish.cp_after}",
        f"    centipawn loss: {rec.stockfish.cpl}",
        f"    mate status: {mate_str}",
        "=" * 80,
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="PGN forensic analyzer for rated games.")
    parser.add_argument("--pgn", type=Path, help="Path to input PGN file.")
    parser.add_argument("--log", type=Path, help="Path to platform log file.")
    parser.add_argument("--positions", type=Path, help="Path to positions JSONL file.")
    parser.add_argument("--engine", default="current", help="Engine under evaluation.")
    parser.add_argument(
        "--color", default="white", choices=["white", "black"], help="MilkyWay color."
    )
    parser.add_argument("--stockfish", default=None, help="Stockfish executable path.")
    parser.add_argument("--nodes", type=int, default=100000, help="SF node budget.")
    parser.add_argument("--skip-stockfish", action="store_true", help="Skip Stockfish.")
    parser.add_argument("--skip-mw02", action="store_true", help="Skip MW-0.2.")
    parser.add_argument("--skip-search", action="store_true", help="Skip search.")
    parser.add_argument(
        "--mw02-dir", type=Path, default=Path("versions/mw_0_2"), help="MW-0.2 path."
    )
    parser.add_argument("--output", type=Path, help="Path to output JSON file.")
    parser.add_argument("--max-moves", type=int, default=None, help="Limit move count.")
    parser.add_argument("--quiet", action="store_true", help="Suppress console blocks.")
    args = parser.parse_args()

    positions: list[dict[str, Any]] = []
    if args.positions and args.positions.exists():
        with open(args.positions, encoding="utf-8") as f:
            positions = [json.loads(line) for line in f if line.strip()]
    elif args.pgn and args.pgn.exists():
        positions = parse_positions_from_pgn(args.pgn, args.log, args.color)
    else:
        default_pos = Path("rated_games/round_25_neomatica/positions.jsonl")
        if default_pos.exists():
            print(f"[INFO] Defaulting to {default_pos}")
            with open(default_pos, encoding="utf-8") as f:
                positions = [json.loads(line) for line in f if line.strip()]
        else:
            parser.error("Either --pgn or --positions must be provided.")

    if args.max_moves:
        positions = positions[: args.max_moves]

    print(f"[INFO] Ingested {len(positions)} positions to analyze.")

    sf_engine: chess.engine.SimpleEngine | None = None
    if not args.skip_stockfish:
        sf_bin = find_stockfish_binary(args.stockfish)
        if sf_bin:
            try:
                print(f"[INFO] Initializing Stockfish from: {sf_bin}")
                sf_engine = chess.engine.SimpleEngine.popen_uci(sf_bin)
                sf_engine.configure({"Threads": 4, "Hash": 128, "UCI_ShowWDL": True})
            except Exception as e:
                print(f"[WARN] Failed to start Stockfish: {e}", file=sys.stderr)
        else:
            print("[WARN] Stockfish binary not found. Skipping SF analysis.", file=sys.stderr)

    mw02_runner: MW02IsolatedRunner | None = None
    if not args.skip_mw02:
        print(f"[INFO] Starting isolated MW-0.2 worker from: {args.mw02_dir}")
        mw02_runner = MW02IsolatedRunner(args.mw02_dir)
        mw02_runner.start()

    current_engine = MilkyWayEngine() if not args.skip_search else None

    records: list[MoveForensicRecord] = []
    t_start = time.monotonic()

    try:
        for idx, pos in enumerate(positions):
            move_num = pos["move_number"]
            ply = pos["ply"]
            fen = pos["fen"]
            played_uci = pos["played_uci"]
            played_san = pos["played_san"]
            time_used = pos.get("time_used_s", 0.0)
            clock_before = pos.get("clock_before_s", 120.0)
            clock_after = pos.get("clock_after_s", clock_before - time_used)
            clock_ms = int(clock_before * 1000)

            board = chess.Board(fen)

            policy_tel = compute_policy_telemetry(board, played_uci)
            search_tel = (
                query_milkyway_search(current_engine, fen, clock_ms)
                if current_engine
                else SearchTelemetry(selected_move=played_uci)
            )
            mw02_tel = (
                mw02_runner.query(fen, clock_ms)
                if mw02_runner
                else MW02Telemetry()
            )
            sf_tel = query_stockfish(sf_engine, board, played_uci, nodes=args.nodes)

            rec = MoveForensicRecord(
                move_number=move_num,
                ply=ply,
                fen=fen,
                played_move=played_uci,
                played_san=played_san,
                time_used_s=time_used,
                clock_remaining_s=clock_after,
                policy=policy_tel,
                milkyway_search=search_tel,
                mw02=mw02_tel,
                stockfish=sf_tel,
            )
            records.append(rec)

            if not args.quiet:
                print(format_report_block(rec))
            elif (idx + 1) % 10 == 0 or idx == len(positions) - 1:
                elapsed = time.monotonic() - t_start
                print(
                    f"  [{idx + 1}/{len(positions)}] Move {move_num}: played={played_san} "
                    f"SF_best={sf_tel.best_san} CPL={sf_tel.cpl} | {elapsed:.1f}s"
                )

    finally:
        if sf_engine:
            sf_engine.quit()
        if mw02_runner:
            mw02_runner.close()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        dump_data = [asdict(r) for r in records]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)
        print(f"[SUCCESS] Wrote full forensic dataset to {args.output}")

    print("\n" + "=" * 80)
    print(f"FORENSIC SUMMARY: {len(records)} MilkyWay decisions analyzed")
    print("=" * 80)
    cpls = [r.stockfish.cpl for r in records if r.stockfish.cpl is not None]
    if cpls:
        inaccuracies = sum(1 for c in cpls if 50 < c <= 120)
        mistakes = sum(1 for c in cpls if 120 < c <= 250)
        major_errors = sum(1 for c in cpls if c > 250)
        zero_cpl = sum(1 for c in cpls if c == 0)
        print("Stockfish Evaluation Profile:")
        print(f"  Zero CPL:          {zero_cpl:3d} ({zero_cpl / len(cpls):.1%})")
        print(f"  Inaccuracies:      {inaccuracies:3d} ({inaccuracies / len(cpls):.1%})")
        print(f"  Mistakes:          {mistakes:3d} ({mistakes / len(cpls):.1%})")
        print(f"  Major Errors:      {major_errors:3d} ({major_errors / len(cpls):.1%})")

    sf_matches = [
        (r.policy.played_rank, r.policy.top_moves, r.stockfish.best_move)
        for r in records
        if r.stockfish.best_move and r.policy.top_moves
    ]
    if sf_matches:
        top1 = sum(1 for _, top, sf in sf_matches if top and top[0]["uci"] == sf)
        top3 = sum(1 for _, top, sf in sf_matches if any(m["uci"] == sf for m in top[:3]))
        top5 = sum(1 for _, top, sf in sf_matches if any(m["uci"] == sf for m in top[:5]))
        n = len(sf_matches)
        print("Policy Accuracy vs Stockfish Best:")
        print(f"  Top-1: {top1}/{n} ({top1 / n:.1%})")
        print(f"  Top-3: {top3}/{n} ({top3 / n:.1%})")
        print(f"  Top-5: {top5}/{n} ({top5 / n:.1%})")

    mw02_compares = [r for r in records if r.mw02.selected_move]
    if mw02_compares:
        mw02_agrees = sum(1 for r in mw02_compares if r.mw02.selected_move == r.played_move)
        rate = mw02_agrees / len(mw02_compares)
        print("MW-0.2 Agreement:")
        print(f"  Identical to Played Move: {mw02_agrees}/{len(mw02_compares)} ({rate:.1%})")
        divergent = [
            (r.move_number, r.played_san, r.played_move, r.mw02.selected_move)
            for r in mw02_compares
            if r.mw02.selected_move != r.played_move
        ]
        if divergent:
            print(f"  Divergent Positions ({len(divergent)}):")
            for m_num, san, played, mw02_m in divergent[:10]:
                print(f"    Move {m_num}: played {san} ({played}) vs MW-0.2 ({mw02_m})")


if __name__ == "__main__":
    main()
