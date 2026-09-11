"""Check root ordering's invariance to a shared policy-logit offset."""
from __future__ import annotations

import hashlib
import importlib
import json
import random
import sys
from pathlib import Path

import chess


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "experiments/compact_quarter_policy_v6_centered"
    sys.path.insert(0, str(candidate))
    ordering = importlib.import_module("move_ordering")
    rng = random.Random(20260912)
    board = chess.Board()
    history = [[[0] * 64 for _ in range(64)] for _ in range(2)]
    for _ in range(256):
        if board.is_game_over() or board.ply() >= 100:
            board = chess.Board()
        legal = list(board.legal_moves)
        scores = {m: rng.uniform(-10, 10) for m in legal}
        tt_move = rng.choice(legal)
        expected = ordering.order_root_moves(board, legal, tt_move, scores, history)
        assert expected[0] == tt_move and set(expected) == set(legal)
        for offset in (-100.0, 100.0):
            shifted = {m: s + offset for m, s in scores.items()}
            assert ordering.order_root_moves(board, legal, tt_move, shifted, history) == expected
        board.push(rng.choice(legal))
    manifest_path = candidate / "candidate_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["change"] = "Center quiet policy logits before clipping, preserving top distinctions"
    manifest["sha256"]["move_ordering.py"] = hashlib.sha256(
        (candidate / "move_ordering.py").read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2))
    (candidate / "ordering_verification.json").write_text(json.dumps({
        "positions": 256, "offsets": [-100, 100], "offset_invariance": True,
        "tt_priority": True, "legal_move_set_preserved": True}, indent=2))
    print("256 positions: offset invariance, TT priority and legal move sets passed")


if __name__ == "__main__":
    main()
