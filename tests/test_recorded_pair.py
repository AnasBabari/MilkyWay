"""Protect paired scoring and preservation of failure evidence."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import chess

from tools.recorded_pair import play_recorded_pair
from tools.test_bank import BankPosition


class RecordedPairTests(unittest.TestCase):
    def test_colour_scoring_and_resume_preserve_games(self) -> None:
        position = BankPosition("test", "opening", chess.STARTING_FEN, 0)
        outcomes = [SimpleNamespace(result="white", termination="checkmate", pgn="white game"),
                    SimpleNamespace(result="black", termination="checkmate", pgn="black game")]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with patch("tools.recorded_pair.play_match", side_effect=outcomes) as play:
                record = play_recorded_pair(Path("a"), Path("b"), position, 1000, 100, directory)
                self.assertEqual(record.pair_score, 2)
                self.assertEqual(play.call_count, 2)
                again = play_recorded_pair(Path("a"), Path("b"), position, 1000, 100, directory)
                self.assertEqual(again, record)
                self.assertEqual(play.call_count, 2)
            self.assertEqual(json.loads((directory / "test_black.json").read_text())["pgn"],
                             "black game")

    def test_void_is_saved_and_never_counted_as_draw(self) -> None:
        position = BankPosition("test", "opening", chess.STARTING_FEN, 0)
        outcome = SimpleNamespace(result="void", termination="init_failure", pgn="failure evidence")
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with (patch("tools.recorded_pair.play_match", return_value=outcome),
                  self.assertRaises(RuntimeError)):
                play_recorded_pair(Path("a"), Path("b"), position, 1000, 100, directory)
            self.assertEqual(json.loads((directory / "test_white.json").read_text())["result"],
                             "void")


if __name__ == "__main__":
    unittest.main()
