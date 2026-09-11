"""Freeze development positions from closed screens, with legal history/provenance."""
from __future__ import annotations

import hashlib
import io
import json
import random
from collections import Counter
from pathlib import Path

import chess
import chess.pgn

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tags(board: chess.Board) -> list[str]:
    result = []
    legal = list(board.legal_moves)
    if board.is_check():
        result.append("check_evasion")
    if any(move.promotion for move in legal):
        result.append("promotion")
    if any(board.is_capture(move) for move in legal):
        result.append("capture_available")
    if any(board.gives_check(move) for move in legal):
        result.append("checking_move_available")
    non_pawns = board.occupied & ~board.pawns & ~board.kings
    if non_pawns.bit_count() <= 4:
        result.append("endgame")
    else:
        result.append("middlegame" if board.fullmove_number >= 12 else "opening")
    if not board.is_check() and "capture_available" not in result:
        result.append("quiet")
    material = [sum(len(board.pieces(p, c)) * v for p, v in
                    ((1, 100), (2, 320), (3, 330), (4, 500), (5, 900)))
                for c in (chess.WHITE, chess.BLACK)]
    if abs(material[0] - material[1]) >= 300:
        result.append("material_imbalance")
    for color in (chess.WHITE, chess.BLACK):
        for square in board.pieces(chess.PAWN, color):
            file, rank = chess.square_file(square), chess.square_rank(square)
            ahead = range(rank + 1, 8) if color else range(rank)
            if not any(chess.square_rank(p) in ahead
                       and abs(chess.square_file(p) - file) <= 1
                       for p in board.pieces(chess.PAWN, not color)):
                result.append("passed_pawn")
                return result
    return result


def main() -> None:
    output = HERE / "probe_suite_01.json"
    assert not output.exists(), "Frozen suite already exists"
    rng = random.Random(20260908)
    curated = [
        ("initial", chess.STARTING_FEN, ["quiet", "opening"]),
        ("opposition_white", "8/8/8/8/4k3/8/4PK2/8 w - - 0 1",
         ["possible_zugzwang", "endgame", "passed_pawn"]),
        ("opposition_black", "8/8/8/8/4k3/8/4PK2/8 b - - 0 1",
         ["possible_zugzwang", "endgame", "passed_pawn"]),
        ("promotion_race", "8/P6k/8/8/8/8/7p/4K3 w - - 0 1",
         ["promotion", "underpromotion_available", "endgame"]),
        ("ep_pin", "4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
         ["ep_pin", "endgame"]),
        ("legal_ep", "6k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
         ["legal_ep", "endgame"]),
        ("castle", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
         ["castling", "endgame"]),
        ("check_evasion", "4r1k1/8/8/8/8/8/8/4K3 w - - 0 1",
         ["check_evasion", "endgame"]),
    ]
    rows = []
    seen = set()
    for label, fen, categories in curated:
        board = chess.Board(fen)
        assert board.is_valid() and not board.is_game_over(), label
        rows.append({"id": label, "fen": board.fen(), "categories": categories,
                     "history_start_fen": board.fen(), "history_uci": [],
                     "source": "team-authored diagnostic position",
                     "source_ply": 0})
        seen.add(board.fen())
    pool = []
    sources = {}
    runs = sorted((ROOT / "experiments").glob("*60s_50g"))
    for run in runs:
        if not (run / "futility_decision.json").exists():
            continue
        for path in sorted((run / "games").glob("*.json")):
            raw = json.loads(path.read_text())
            game = chess.pgn.read_game(io.StringIO(raw["pgn"]))
            assert game is not None and not game.errors
            board = game.board()
            history: list[str] = []
            candidate_lost = raw["result"] not in (raw["candidate_color"], "draw")
            source = str(path.relative_to(ROOT)).replace("\\", "/")
            for ply, move in enumerate(game.mainline_moves(), 1):
                assert move in board.legal_moves
                board.push(move)
                history.append(move.uci())
                if ply % 12 or board.is_game_over() or board.fen() in seen:
                    continue
                seen.add(board.fen())
                categories = tags(board)
                if candidate_lost:
                    categories.append("recorded_loss")
                pool.append({"fen": board.fen(), "categories": categories,
                             "history_start_fen": raw["start_fen"],
                             "history_uci": list(history), "source": source,
                             "source_sha256": digest(path), "source_ply": ply})
    rng.shuffle(pool)
    selected = set()
    # Cover rarer features before filling a broad deterministic sample.
    for category in ("promotion", "check_evasion", "endgame", "passed_pawn",
                     "quiet", "opening", "middlegame", "material_imbalance",
                     "checking_move_available", "recorded_loss"):
        count = 0
        for index, row in enumerate(pool):
            if index not in selected and category in row["categories"]:
                selected.add(index)
                count += 1
                if count == 16:
                    break
    for index in range(len(pool)):
        if len(selected) + len(rows) >= 240:
            break
        selected.add(index)
    for index in sorted(selected):
        row = pool[index]
        row["id"] = f"recorded_{len(rows):03d}"
        rows.append(row)
        sources[row["source"]] = row["source_sha256"]
    assert len(rows) == 240
    categories = Counter(tag for row in rows for tag in row["categories"])
    result = {"purpose": "development probes only; never independent confirmation",
              "seed": 20260908, "builder_sha256": digest(Path(__file__)),
              "tag_caveat": "Structural tags, not oracle-certified tactics or zugzwang.",
              "position_count": len(rows), "category_counts": dict(categories),
              "source_sha256": sources, "positions": rows}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"positions": len(rows), "sha256": digest(output),
                      "categories": dict(categories)}))


if __name__ == "__main__":
    main()
