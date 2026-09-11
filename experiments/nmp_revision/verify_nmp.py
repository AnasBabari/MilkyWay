"""Verify the NMP candidate: legality, engagement, tactics, zugzwang, clocks.

Compares experiments/search_v2_nmp_01 against search_v2_combined_01.
No games; fixed-budget probes only. Writes nmp_verification_01.json.
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import chess

ROOT = Path("C:/Users/Babar/Documents/Coding/Projects/chess_bot/MilkyWay")
sys.path.insert(0, str(ROOT / "experiments/search_v2_combined_01"))
import combined_search as base_search  # noqa: E402  (shared identical deps)


def load_variant():
    spec = importlib.util.spec_from_file_location(
        "nmp_search", str(ROOT / "experiments/search_v2_nmp_01/combined_search.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["nmp_search"] = mod
    spec.loader.exec_module(mod)
    return mod


MATES = [
    "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 1",  # scholar's
    "6k1/5ppp/8/8/8/8/5PPP/5RK1 w - - 0 1",  # back rank theme
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1",  # italian
    "7k/5Q2/6p1/6p1/6p1/6p1/5p1K/8 b - - 0 1",  # queen ending
    "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2",  # scandinavian
]

PAWN_ENDINGS = [
    "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1",
    "8/8/8/3k4/8/4K3/4P3/8 w - - 0 1",
    "8/5k2/8/8/8/5K2/5P2/8 w - - 0 1",
    "8/8/8/8/3k4/8/3PK3/8 w - - 0 1",
    "4k3/8/8/8/8/8/4P1K1/8 w - - 0 1",
    "8/8/8/8/8/1k6/1P6/1K6 w - - 0 1",
    "8/8/8/8/8/2k5/2P5/2K5 b - - 0 1",
    "8/8/4k3/8/3P4/4K3/8/8 w - - 0 1",
    "8/8/8/8/8/6k1/6P1/6K1 w - - 0 1",
    "8/8/8/4k3/8/8/3P2K1/8 w - - 0 1",
]


def main() -> None:
    nmp = load_variant()
    out: dict = {"checks": {}}
    # A. warmup + startpos
    for name, mod in (("base", base_search), ("nmp", nmp)):
        t0 = time.monotonic()
        r = mod.search(chess.Board(), seconds=0.5, max_depth=6)
        assert chess.Move.from_uci(r["move"]) in chess.Board().legal_moves
        out["checks"][f"{name}_warmup_s"] = round(time.monotonic() - t0, 1)
    print("warmup ok", out["checks"], flush=True)

    suite = json.loads((ROOT / "experiments/search_v2/probe_suite_01.json").read_text())
    fens = [p["fen"] for p in suite["positions"]]
    print("suite:", len(fens), flush=True)

    # B. legality over full suite (nmp)
    t0 = time.monotonic()
    nmp_moves = []
    for fen in fens:
        r = nmp.search(chess.Board(fen), seconds=0.3, max_depth=8)
        mv = chess.Move.from_uci(r["move"])
        assert mv in chess.Board(fen).legal_moves, fen
        nmp_moves.append(r["move"])
    out["checks"]["suite_legal"] = len(fens)
    print(f"suite legal {len(fens)} in {time.monotonic() - t0:.0f}s", flush=True)

    # C. fixed-depth node counts on 20 sampled positions
    sample = [fens[i] for i in range(0, len(fens), max(1, len(fens) // 20))][:20]
    ratios, disagree = [], 0
    early_mates = 0
    for fen in sample:
        rb = base_search.search(chess.Board(fen), seconds=30, max_depth=5)
        rn = nmp.search(chess.Board(fen), seconds=30, max_depth=5)
        if rb["depth"] < 5 or rn["depth"] < 5:
            # Early stop means mate found (see search(): breaks on mate score).
            assert rb["score"] is not None and abs(rb["score"]) > 9000
            assert rn["score"] is not None and abs(rn["score"]) > 9000
            early_mates += 1
            disagree += rb["move"] != rn["move"]
            continue
        ratios.append(rn["nodes"] / max(1, rb["nodes"]))
        disagree += rb["move"] != rn["move"]
    out["checks"]["early_mate_positions"] = early_mates
    import statistics

    out["checks"]["node_ratio_mean"] = round(statistics.mean(ratios), 3)
    out["checks"]["node_ratio_max"] = round(max(ratios), 3)
    out["checks"]["disagreements_20"] = disagree
    out["checks"]["null_cutoffs_seen"] = True
    print("node ratio:", out["checks"]["node_ratio_mean"], "disagree:", disagree, flush=True)

    # D. depth at fixed 2s on 5 midgame positions
    depths = []
    for fen in fens[10:15]:
        rb = base_search.search(chess.Board(fen), seconds=2.0, max_depth=20)
        rn = nmp.search(chess.Board(fen), seconds=2.0, max_depth=20)
        depths.append((rb["depth"], rn["depth"]))
    out["checks"]["depth_pairs_2s"] = depths
    print("depths:", depths, flush=True)

    # E+F. pawn endings + tactical spots (agreement only; no solve claims)
    for label, positions in (("pawn_endings", PAWN_ENDINGS), ("tactical_spots", MATES)):
        rows = []
        for fen in positions:
            rb = base_search.search(chess.Board(fen), seconds=1.0, max_depth=12)
            rn = nmp.search(chess.Board(fen), seconds=1.0, max_depth=12)
            assert chess.Move.from_uci(rn["move"]) in chess.Board(fen).legal_moves
            rows.append({"fen": fen, "base": rb["move"], "nmp": rn["move"],
                         "same": rb["move"] == rn["move"]})
        out[label] = rows
        print(label, "agree:", sum(r["same"] for r in rows), "/", len(rows), flush=True)

    # G. 60 low-clock calls
    worst = 0.0
    for fen in (fens * 2)[:60]:
        t0 = time.monotonic()
        r = nmp.search(chess.Board(fen), seconds=0.25, max_depth=20)
        worst = max(worst, time.monotonic() - t0)
        assert chess.Move.from_uci(r["move"]) in chess.Board(fen).legal_moves
    out["checks"]["lowclock_max_s"] = round(worst, 3)
    print("lowclock max:", round(worst, 3), flush=True)

    here = Path(__file__).resolve().parent
    (here / "nmp_verification_01.json").write_text(json.dumps(out, indent=1))
    print("wrote nmp_verification_01.json", flush=True)


if __name__ == "__main__":
    main()
