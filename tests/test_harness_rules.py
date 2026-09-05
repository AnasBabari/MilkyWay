"""Tests for upstream 600-ply draw and flag rules in harness/referee.py."""

from __future__ import annotations

import unittest

import chess

from harness.referee import play_match
from harness.rules import PLY_CAP
from harness.sandbox import Agent, AgentFailure


class ScriptedAgent(Agent):
    """Test agent that returns scripted moves or fails predictably."""

    def __init__(
        self,
        moves: list[str] | None = None,
        fail_reason: str | None = None,
        delay_s: float = 0.0,
    ) -> None:
        super().__init__(command=[])
        self.moves = list(moves or [])
        self.move_idx = 0
        self.fail_reason = fail_reason
        self.delay_s = delay_s
        self.stopped = False

    def start(self, init_budget_s: float) -> None:
        if self.fail_reason == "init":
            raise AgentFailure("init")

    def stop(self) -> None:
        self.stopped = True

    def move(self, fen: str, time_left_ms: int) -> str:
        if self.fail_reason and self.fail_reason != "init":
            raise AgentFailure(self.fail_reason)
        if self.move_idx < len(self.moves):
            mv = self.moves[self.move_idx]
            self.move_idx += 1
            return mv
        board = chess.Board(fen)
        for legal in board.legal_moves:
            return legal.uci()
        raise RuntimeError("No legal moves available")


class HarnessRulesRegressionTests(unittest.TestCase):
    def test_default_ply_cap_constant_is_600(self) -> None:
        """Verify PLY_CAP was updated from 300 to 600."""
        self.assertEqual(PLY_CAP, 600)

    def test_300_plies_does_not_terminate(self) -> None:
        """A game reaching 300 plies must not terminate under 600-ply cap."""
        # Start at fullmove 150 Black to move -> ply 299.
        # White has king and queen, Black has king.
        # Next move reaches ply 300.
        # Under the old harness (PLY_CAP=300), this would terminate by adjudication.
        # Under new harness (PLY_CAP=600), it continues.
        fen = "8/8/8/8/8/4k3/4Q3/4K3 b - - 0 150"
        board = chess.Board(fen)
        self.assertEqual(board.ply(), 299)

        black = ScriptedAgent(moves=["e3d4"])
        white = ScriptedAgent(moves=["e2e3"])

        # Run with default ply_cap (600) and ample clock.
        outcome = play_match(white, black, base_ms=10000, increment_ms=1000, start_fen=fen)

        # Black played 1 move (ply 300 reached and passed).
        # The game should NOT have ended at ply 300.
        # In fact, white should have moved at ply 300 to e2e3.
        self.assertNotIn(outcome.termination, ("adjudication", "ply_cap"))

    def test_599_plies_does_not_trigger_cap(self) -> None:
        """At 599 plies the game is not yet capped; the next move is allowed."""
        # Fullmove 300, Black to move -> (300-1)*2 + 1 = 599 plies.
        fen = "8/8/8/8/8/4k3/4Q3/4K3 b - - 0 300"
        board = chess.Board(fen)
        self.assertEqual(board.ply(), 599)

        # Black makes move at 599 plies, bringing ply to 600.
        # Then next iteration at 600 plies triggers ply_cap.
        black = ScriptedAgent(moves=["e3d4"])
        white = ScriptedAgent(moves=["e2e3"])

        outcome = play_match(white, black, base_ms=10000, increment_ms=1000, start_fen=fen)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "ply_cap")
        # Ensure black actually executed the move at ply 599
        self.assertEqual(black.move_idx, 1)
        self.assertEqual(white.move_idx, 0)

    def test_600_plies_triggers_draw_by_ply_cap(self) -> None:
        """At 600 plies referee returns result='draw', termination='ply_cap'."""
        # Fullmove 301, White to move -> (301-1)*2 = 600 plies.
        fen = "8/8/8/8/8/4k3/4Q3/4K3 w - - 0 301"
        board = chess.Board(fen)
        self.assertEqual(board.ply(), 600)

        white = ScriptedAgent(moves=["e2e3"])
        black = ScriptedAgent(moves=["e3d4"])

        outcome = play_match(white, black, base_ms=10000, increment_ms=1000, start_fen=fen)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "ply_cap")
        # Referee terminated at start of loop without asking white to move
        self.assertEqual(white.move_idx, 0)
        self.assertEqual(black.move_idx, 0)

    def test_opening_fen_ply_contributes_correctly_through_board_ply(self) -> None:
        """Verify board.ply() counts FEN fullmove number and turn towards cap."""
        # Contrast with old harness which used len(board.move_stack) >= ply_cap.
        # Here we test a custom ply_cap=10 from an opening FEN already at ply 8.
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 5"  # White move 5 -> ply 8
        board = chess.Board(fen)
        self.assertEqual(board.ply(), 8)

        # Move 1 (White): ply 8 -> 9
        # Move 2 (Black): ply 9 -> 10
        # Reaching ply 10 triggers cap.
        white = ScriptedAgent(moves=["e2e4"])
        black = ScriptedAgent(moves=["e7e5"])

        outcome = play_match(
            white, black, base_ms=10000, increment_ms=1000, ply_cap=10, start_fen=fen
        )
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "ply_cap")
        self.assertEqual(white.move_idx, 1)
        self.assertEqual(black.move_idx, 1)

    def test_flag_normally_loses_when_opponent_has_mating_material(self) -> None:
        """When mover flags and opponent has mating material, mover loses."""
        # White has bare King, Black has King + Queen. Not in check/checkmate. White flags.
        fen = "q7/8/8/8/8/4k3/8/4K3 w - - 0 1"
        board = chess.Board(fen)
        self.assertIsNone(board.outcome())
        self.assertFalse(board.has_insufficient_material(chess.BLACK))

        # Base clock is 0 ms with 0 increment, causing White to flag immediately.
        white = ScriptedAgent(moves=["e1d1"])
        black = ScriptedAgent()

        outcome = play_match(white, black, base_ms=0, increment_ms=0, start_fen=fen)
        self.assertEqual(outcome.result, "black")
        self.assertEqual(outcome.termination, "flag")

    def test_flag_is_draw_when_opponent_has_insufficient_mating_material(self) -> None:
        """When mover flags but opponent has insufficient mating material, it is a draw."""
        # White has King + Queen, Black has bare King. White flags.
        fen = "8/8/8/8/8/4k3/4Q3/4K3 w - - 0 1"
        board = chess.Board(fen)
        self.assertIsNone(board.outcome())
        self.assertTrue(board.has_insufficient_material(chess.BLACK))

        white = ScriptedAgent(moves=["e2e3"])
        black = ScriptedAgent()

        outcome = play_match(white, black, base_ms=0, increment_ms=0, start_fen=fen)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "flag")

    def test_existing_checkmate_preserved(self) -> None:
        """Checkmate terminates with winning side."""
        # Scholar's mate sequence
        white = ScriptedAgent(moves=["e2e4", "d1h5", "f1c4", "h5f7"])
        black = ScriptedAgent(moves=["e7e5", "b8c6", "g8f6"])

        outcome = play_match(white, black, base_ms=10000, increment_ms=500)
        self.assertEqual(outcome.result, "white")
        self.assertEqual(outcome.termination, "checkmate")

    def test_existing_stalemate_preserved(self) -> None:
        """Stalemate terminates with draw."""
        # Black king at a8 trapped, not in check. Black to move.
        fen = "k7/8/1Q6/8/8/8/8/7K b - - 0 1"
        black = ScriptedAgent()
        white = ScriptedAgent()

        outcome = play_match(white, black, base_ms=10000, increment_ms=500, start_fen=fen)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "stalemate")

    def test_existing_fifty_moves_draw_preserved(self) -> None:
        """50-move rule without captures or pawn pushes terminates as fifty_moves draw."""
        # Halfmove clock at 99 with sufficient material (Rook on each side).
        # White makes non-pawn non-capture move to hit 100 halfmoves.
        fen = "8/8/8/8/8/4k3/4r3/4K2R w - - 99 100"
        white = ScriptedAgent(moves=["h1h3"])
        black = ScriptedAgent(moves=["e3f4"])

        outcome = play_match(white, black, base_ms=10000, increment_ms=500, start_fen=fen)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "fifty_moves")

    def test_existing_threefold_repetition_preserved(self) -> None:
        """Threefold repetition terminates as threefold_repetition draw."""
        # Repeat knight moves back and forth
        white = ScriptedAgent(moves=["g1f3", "f3g1", "g1f3", "f3g1"])
        black = ScriptedAgent(moves=["g8f6", "f6g8", "g8f6", "f6g8"])

        outcome = play_match(white, black, base_ms=10000, increment_ms=500)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "threefold_repetition")

    def test_existing_illegal_move_preserved(self) -> None:
        """Illegal move forfeits the game to opponent."""
        white = ScriptedAgent(moves=["e2e5"])  # Illegal pawn move
        black = ScriptedAgent()

        outcome = play_match(white, black, base_ms=10000, increment_ms=500)
        self.assertEqual(outcome.result, "black")
        self.assertEqual(outcome.termination, "illegal")

    def test_existing_crash_preserved(self) -> None:
        """Agent crash forfeits the game to opponent."""
        white = ScriptedAgent(fail_reason="crash")
        black = ScriptedAgent()

        outcome = play_match(white, black, base_ms=10000, increment_ms=500)
        self.assertEqual(outcome.result, "black")
        self.assertEqual(outcome.termination, "crash")


if __name__ == "__main__":
    unittest.main()
