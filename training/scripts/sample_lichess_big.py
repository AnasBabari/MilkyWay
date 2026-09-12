"""MilkyWay — large lichess transcript sampler -> PGN.

Streams `lichess_200k_elo_bins.csv` (5.95M rows, Elo-binned) from its zip and
stratified-samples tens of thousands of strong games (Elo >= 2000), replayed
through python-chess to validate legal play, written as a PGN mirroring the
`Lichess200k.pgn` format the rest of the pipeline already ingests.

  training/.venv/Scripts/python.exe training/scripts/sample_lichess_big.py \\
      --zip training/data/hf_raw/lichess_200k_elo_bins.zip \\
      --out training/data/raw_pgn/LichessBig.pgn --target-games 40000
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess  # noqa: E402

# Keep rate per Elo bin lower bound. Stronger games are oversampled so the
# corpus concentrates on high-quality play while still covering 2000-2200.
BIN_KEEP_RATES: dict[tuple[int, int], float] = {
    (2000, 2200): 0.015,
    (2200, 2400): 0.040,
    (2400, 2600): 0.10,
    (2600, 2700): 0.25,
    (2700, 2900): 0.55,
    (2900, 3200): 0.90,
}

BIN_RE = re.compile(r"\[(\d+),\s*(\d+)\)")
MOVE_NUM_RE = re.compile(r"^\d+\.")
RESULT_TOK = re.compile(r"^(1-0|0-1|1/2-1/2)$")

# Hard per-bin caps so the sample stays balanced across the whole strength range.
BIN_CAPS: dict[tuple[int, int], int] = {
    (2000, 2100): 9000,
    (2100, 2200): 8000,
    (2200, 2300): 7000,
    (2300, 2400): 6000,
    (2400, 2500): 5000,
    (2500, 2600): 4000,
    (2600, 2700): 3000,
    (2700, 2800): 2500,
    (2800, 2900): 1200,
    (2900, 3000): 400,
    (3000, 3100): 300,
    (3100, 3200): 200,
}


def bin_bounds(bin_str: str) -> tuple[int, int]:
    """Parse an Elo-bin label like '[2000, 2100)' into (lo, hi)."""
    m = BIN_RE.search(bin_str or "")
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


def keep_rate(bounds: tuple[int, int]) -> float:
    lo, _ = bounds
    for (blo, bhi), rate in BIN_KEEP_RATES.items():
        if lo >= blo and lo < bhi:
            return rate
    return 0.0


def cap_for(bounds: tuple[int, int]) -> int:
    lo, _ = bounds
    for (blo, bhi), cap in BIN_CAPS.items():
        if lo >= blo and lo < bhi:
            return cap
    return 0


def stable_keep(idx: int, rate: float) -> bool:
    """Deterministic per-row keep decision without storing a PRNG state."""
    if rate <= 0.0:
        return False
    if rate >= 1.0:
        return True
    h = int(hashlib.md5(str(idx).encode()).hexdigest()[:8], 16)
    return (h % 100000) < int(rate * 100000)


def row_moves(transcript: str) -> list[str] | None:
    """Replay a transcript with python-chess; return UCI moves or None."""
    toks = [t for t in transcript.split() if not RESULT_TOK.match(t)]
    # Move numbers ("1.") are glued to the move token in this dataset: "1.e4".
    toks = [MOVE_NUM_RE.sub("", t) for t in toks]
    board = chess.Board()
    moves: list[str] = []
    for tok in toks:
        if tok in ("1-0", "0-1", "1/2-1/2"):
            continue
        if not tok:
            continue
        try:
            mv = board.parse_san(tok)
        except (ValueError, KeyError):
            return None
        if mv not in board.legal_moves:
            return None
        board.push(mv)
        moves.append(mv.uci())
    return moves


def write_pgn_game(
    out: TextIO,
    idx: int,
    white_elo: str,
    black_elo: str,
    result: str,
    moves: list[str],
) -> None:
    n_ply = len(moves)
    assert isinstance(out, io.TextIOWrapper)
    out.write('[Event "LichessBig"]\n')
    out.write(f'[White "Lichess{idx}"]\n')
    out.write(f'[Black "LichessOpp{idx}"]\n')
    out.write(f'[Result "{result}"]\n')
    out.write(f'[WhiteElo "{white_elo}"]\n')
    out.write(f'[BlackElo "{black_elo}"]\n\n')
    # Compact ply numbering: "1. e4 c5 2. Nf3 d6 ... <result>"
    parts: list[str] = []
    for ply in range(0, n_ply, 2):
        fullmove = ply // 2 + 1
        w = moves[ply]
        parts.append(f"{fullmove}. {w}")
        if ply + 1 < n_ply:
            parts.append(moves[ply + 1])
    out.write(" ".join(parts))
    out.write(f" {result}\n\n")


def cap_reached(bin_str: str, per_bin: dict[str, int], bounds: tuple[int, int]) -> bool:
    return per_bin.get(bin_str, 0) >= cap_for(bounds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zip", type=Path, default=ROOT / "training/data/hf_raw/lichess_200k_elo_bins.zip"
    )
    parser.add_argument("--out", type=Path, default=ROOT / "training/data/raw_pgn/LichessBig.pgn")
    parser.add_argument("--max-games", type=int, default=50000)
    parser.add_argument(
        "--cap-scale",
        type=float,
        default=1.0,
        help="Multiply every per-Elo-bin cap by this factor (corpus expansion).",
    )
    parser.add_argument(
        "--rate-scale",
        type=float,
        default=1.0,
        help="Multiply every per-bin keep rate by this factor (capped at 1.0).",
    )
    args = parser.parse_args()

    if args.cap_scale != 1.0:
        for key in list(BIN_CAPS):
            BIN_CAPS[key] = int(BIN_CAPS[key] * args.cap_scale)
    if args.rate_scale != 1.0:
        for key in list(BIN_KEEP_RATES):
            BIN_KEEP_RATES[key] = min(1.0, BIN_KEEP_RATES[key] * args.rate_scale)

    kept = 0
    scanned = 0
    per_bin: dict[str, int] = {}
    with zipfile.ZipFile(args.zip) as zf:
        name = zf.namelist()[0]
        with zf.open(name, "r") as fh, args.out.open("w", encoding="utf-8") as out:
            text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
            reader = csv.DictReader(text)
            for idx, row in enumerate(reader):
                if idx == 0:
                    continue
                bin_str = (row.get("elo_bin") or "").strip('"')
                bounds = bin_bounds(bin_str)
                rate = keep_rate(bounds)
                if rate <= 0.0 or cap_reached(bin_str, per_bin, bounds):
                    continue
                if not stable_keep(idx, rate):
                    continue
                scanned += 1
                transcript = row.get("transcript") or ""
                moves = row_moves(transcript)
                if moves is None or not moves:
                    continue
                result = (row.get("Result") or "").strip()
                if result not in ("1-0", "0-1", "1/2-1/2"):
                    continue
                write_pgn_game(
                    out,
                    kept,
                    (row.get("WhiteElo") or "0").strip(),
                    (row.get("BlackElo") or "0").strip(),
                    result,
                    moves,
                )
                kept += 1
                per_bin[bin_str] = per_bin.get(bin_str, 0) + 1
                if kept >= args.max_games:
                    break
    print(f"kept {kept} games (scanned candidates {scanned})")
    print("per_bin:", dict(sorted(per_bin.items())))
    print(f"wrote {args.out} ({args.out.stat().st_size if args.out.exists() else 0} bytes)")


if __name__ == "__main__":
    main()
