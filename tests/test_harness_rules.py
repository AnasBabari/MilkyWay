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

    def test_300_ply_position_does_not_end(self) -> None:
        """A game reaching 300 plies must not terminate under 600-ply cap."""
        # Fullmove 150 Black to move -> (150-1)*2 + 1 = 299 plies.
        # Position: White King e1, Queen d1; Black King e7. Valid board.
        fen = "8/4k3/8/8/8/8/8/3QK3 b - - 0 150"
        board = chess.Board(fen)
        self.assertTrue(board.is_valid())
        self.assertEqual(board.ply(), 299)

        # Move 1 (Black): e7e6 brings ply to 300.
        # Move 2 (White): d1d2 at ply 300. Under old 300-ply cap, this would be blocked.
        # Move 3 (Black): e6e5 at ply 301.
        black = ScriptedAgent(moves=["e7e6", "e6e5"])
        white = ScriptedAgent(moves=["d1d2"])

        # Under ply_cap=300, game would terminate at ply 300 before White moves.
        outcome_capped_300 = play_match(
            white, black, base_ms=10000, increment_ms=1000, ply_cap=300, start_fen=fen
        )
        self.assertEqual(outcome_capped_300.termination, "ply_cap")
        self.assertEqual(white.move_idx, 0)

        # Under new default ply_cap=600, game does not end at ply 300; White moves.
        white.move_idx = 0
        black.move_idx = 0
        outcome = play_match(white, black, base_ms=10000, increment_ms=1000, start_fen=fen)
        self.assertNotIn(outcome.termination, ("adjudication", "ply_cap"))
        self.assertGreaterEqual(white.move_idx, 1)

    def test_300_plies_does_not_terminate(self) -> None:
        """Alias for test_300_ply_position_does_not_end."""
        self.test_300_ply_position_does_not_end()

    def test_599_plies_does_not_trigger_cap(self) -> None:
        """At 599 plies the game is not yet capped; the next move is allowed."""
        # Fullmove 300, Black to move -> (300-1)*2 + 1 = 599 plies. Valid board.
        fen = "8/4k3/8/8/8/8/8/3QK3 b - - 0 300"
        board = chess.Board(fen)
        self.assertTrue(board.is_valid())
        self.assertEqual(board.ply(), 599)

        # Black makes legal move at 599 plies (e7e6), bringing ply to 600.
        # Then next iteration at 600 plies triggers ply_cap before White moves.
        black = ScriptedAgent(moves=["e7e6"])
        white = ScriptedAgent(moves=["d1d2"])

        outcome = play_match(white, black, base_ms=10000, increment_ms=1000, start_fen=fen)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "ply_cap")
        self.assertEqual(black.move_idx, 1)
        self.assertEqual(white.move_idx, 0)

    def test_600_ply_cap_is_draw(self) -> None:
        """At 600 plies referee returns result='draw', termination='ply_cap'."""
        # Fullmove 301, White to move -> (301-1)*2 = 600 plies. Valid board.
        fen = "8/4k3/8/8/8/8/8/3QK3 w - - 0 301"
        board = chess.Board(fen)
        self.assertTrue(board.is_valid())
        self.assertEqual(board.ply(), 600)

        white = ScriptedAgent(moves=["d1d2"])
        black = ScriptedAgent(moves=["e7e6"])

        outcome = play_match(white, black, base_ms=10000, increment_ms=1000, start_fen=fen)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "ply_cap")
        # Referee terminated at start of loop without asking white to move
        self.assertEqual(white.move_idx, 0)
        self.assertEqual(black.move_idx, 0)

    def test_600_plies_triggers_draw_by_ply_cap(self) -> None:
        """Alias for test_600_ply_cap_is_draw."""
        self.test_600_ply_cap_is_draw()

    def test_opening_fen_ply_contributes_correctly_through_board_ply(self) -> None:
        """Verify board.ply() counts FEN fullmove number and turn towards cap."""
        # Contrast with old harness which used len(board.move_stack) >= ply_cap.
        # Test custom ply_cap=10 from an opening FEN already at ply 8.
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 5"  # White move 5 -> ply 8
        board = chess.Board(fen)
        self.assertEqual(board.ply(), 8)

        white = ScriptedAgent(moves=["e2e4"])
        black = ScriptedAgent(moves=["e7e5"])

        outcome = play_match(
            white, black, base_ms=10000, increment_ms=1000, ply_cap=10, start_fen=fen
        )
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "ply_cap")
        self.assertEqual(white.move_idx, 1)
        self.assertEqual(black.move_idx, 1)

    def test_curated_deep_fen_reaches_600_ply_cap(self) -> None:
        """A game starting at move 296 (ply 590) terminates at ply 600 after 10 plies."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 296"  # ply 590
        board = chess.Board(fen)
        self.assertEqual(board.ply(), 590)

        # 5 quiet pawn moves each = 10 plies -> reaches ply 600
        white_moves = ["a2a3", "b2b3", "c2c3", "d2d3", "e2e3"]
        black_moves = ["a7a6", "b7b6", "c7c6", "d7d6", "e7e6"]
        white = ScriptedAgent(moves=white_moves)
        black = ScriptedAgent(moves=black_moves)

        outcome = play_match(white, black, base_ms=10000, increment_ms=1000, start_fen=fen)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "ply_cap")
        self.assertEqual(white.move_idx, 5)
        self.assertEqual(black.move_idx, 5)

    def test_flag_vs_mating_material_is_loss(self) -> None:
        """When mover flags and opponent has mating material, mover loses."""
        # White has Queen + King, Black has bare King. Black to move.
        fen = "8/4k3/8/8/8/8/8/3QK3 b - - 0 1"
        board = chess.Board(fen)
        self.assertTrue(board.is_valid())
        self.assertIsNone(board.outcome())
        self.assertFalse(board.has_insufficient_material(chess.WHITE))

        white = ScriptedAgent()
        black = ScriptedAgent(moves=["e7e6"])

        outcome = play_match(white, black, base_ms=0, increment_ms=0, start_fen=fen)
        self.assertEqual(outcome.result, "white")
        self.assertEqual(outcome.termination, "flag")

    def test_flag_normally_loses_when_opponent_has_mating_material(self) -> None:
        """Alias for test_flag_vs_mating_material_is_loss."""
        self.test_flag_vs_mating_material_is_loss()

    def test_flag_vs_bare_king_is_draw_when_opponent_cannot_mate(self) -> None:
        """When mover flags but opponent has bare king (insufficient material), it is a draw."""
        # White has King + Queen, Black has bare King. White to move.
        fen = "8/4k3/8/8/8/8/8/3QK3 w - - 0 1"
        board = chess.Board(fen)
        self.assertTrue(board.is_valid())
        self.assertIsNone(board.outcome())
        self.assertTrue(board.has_insufficient_material(chess.BLACK))

        white = ScriptedAgent(moves=["d1d2"])
        black = ScriptedAgent()

        outcome = play_match(white, black, base_ms=0, increment_ms=0, start_fen=fen)
        self.assertEqual(outcome.result, "draw")
        self.assertEqual(outcome.termination, "flag")

    def test_flag_is_draw_when_opponent_has_insufficient_mating_material(self) -> None:
        """Alias for test_flag_vs_bare_king_is_draw_when_opponent_cannot_mate."""
        self.test_flag_vs_bare_king_is_draw_when_opponent_cannot_mate()

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
