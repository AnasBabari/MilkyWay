"""MilkyWay M17 — Public GM PGN downloader.

Downloads curated high-quality standard chess games from grandmaster archives
into training/data/raw_pgn/ for offline dataset extraction.
All PGN files are gitignored.
"""

from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PLAYERS = ["Kasparov", "Carlsen", "Karpov", "Fischer", "Anand", "Kramnik"]
BASE_URL = "https://www.pgnmentor.com/players/{player}.zip"


def download_player_pgns(output_dir: Path, max_players: int = 4) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded_files: list[Path] = []

    for player in PLAYERS[:max_players]:
        target_pgn = output_dir / f"{player}.pgn"
        if target_pgn.exists() and target_pgn.stat().st_size > 10000:
            print(f"Using cached {target_pgn.name} ({target_pgn.stat().st_size / 1024:.1f} KB)")
            downloaded_files.append(target_pgn)
            continue

        url = BASE_URL.format(player=player)
        print(f"Downloading {player} games from {url}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
            zf = zipfile.ZipFile(io.BytesIO(content))
            pgn_filename = zf.namelist()[0]
            with zf.open(pgn_filename) as src, open(target_pgn, "wb") as dst:
                dst.write(src.read())
            print(f"Saved {target_pgn.name} ({target_pgn.stat().st_size / 1024:.1f} KB)")
            downloaded_files.append(target_pgn)
        except Exception as e:
            print(f"Failed to download {player}: {e}", file=sys.stderr)

    return downloaded_files


if __name__ == "__main__":
    out_dir = ROOT / "training" / "data" / "raw_pgn"
    download_player_pgns(out_dir)
