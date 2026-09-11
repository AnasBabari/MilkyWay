"""Select balanced master-game training openings, excluding all existing arena banks."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import chess
import chess.engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from baselines.stockfish.agent import find_stockfish_binary  # noqa: E402
from tools.confirm_bank import CONFIRM_TEST_BANK  # noqa: E402
from tools.screen_bank import SCREEN_TEST_BANK  # noqa: E402
from tools.test_bank import PAIRED_TEST_BANK  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--count", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()
    assert not args.out.exists()
    excluded = {" ".join(p.fen.split()[:4])
                for bank in (CONFIRM_TEST_BANK, SCREEN_TEST_BANK, PAIRED_TEST_BANK) for p in bank}
    candidates = []
    for line in args.records.read_text().splitlines():
        record = json.loads(line)
        board = chess.Board(record["fen"])
        if (8 <= board.ply() <= 20 and board.is_valid() and not board.is_game_over()
                and " ".join(board.fen().split()[:4]) not in excluded):
            candidates.append(record)
    random.Random(args.seed).shuffle(candidates)
    binary = find_stockfish_binary()
    assert binary
    selected = []
    games = set()
    fens = set()
    with chess.engine.SimpleEngine.popen_uci(binary) as oracle:
        oracle.configure({"Threads": 1, "Hash": 16, "Skill Level": 20})
        for record in candidates:
            game_id = record["source_game_id"]
            board = chess.Board(record["fen"])
            key = " ".join(board.fen().split()[:4])
            if game_id in games or key in fens:
                continue
            result = oracle.analyse(board, chess.engine.Limit(nodes=50000), game=game_id)
            cp = result["score"].pov(board.turn).score(mate_score=10000)
            if abs(cp) > 80:
                continue
            selected.append({"fen": board.fen(), "source_game_id": game_id,
                             "source_position_id": record["position_id"], "teacher_cp_stm": cp})
            games.add(game_id)
            fens.add(key)
            if len(selected) == args.count:
                break
    assert len(selected) == args.count
    manifest = {"positions": selected, "source": str(args.records.resolve()),
                "source_sha256": hashlib.sha256(args.records.read_bytes()).hexdigest(),
                "stockfish_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                "teacher_nodes": 50000, "teacher_skill": 20, "seed": args.seed,
                "excluded_bank_positions": len(excluded),
                "purpose": "training only; distinct source games; no evaluation-bank starts"}
    args.out.write_text(json.dumps(manifest, indent=2))
    print(f"Selected {len(selected)} balanced training openings")


if __name__ == "__main__":
    main()
