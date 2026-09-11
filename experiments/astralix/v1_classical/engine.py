"""MilkyWay persistent engine: game history, time control, search orchestration."""

from __future__ import annotations

import contextlib
import math

import chess

from constants import INF, MATE_SCORE
from evaluation import evaluate
from root_policy import get_root_evaluator
from search import MATE_THRESHOLD, Searcher
from time_manager import Clock, allocate_time
from transposition import TranspositionTable

DEBUG: bool = False


class MilkyWayEngine:
    """One instance lives for a whole game (module-level singleton)."""

    def __init__(self) -> None:
        self.tt = TranspositionTable(max_entries=131072)
        self.searcher = Searcher(self.tt)
        self.seen_keys: dict[int, int] = {}
        self.last_fen: str | None = None
        self._last_score: int | None = None

    def reset_game(self) -> None:
        self.searcher.new_game()
        self.seen_keys.clear()
        self.last_fen = None
        self._last_score = None

    def _track_position(self, board: chess.Board) -> None:
        key = board._transposition_key()
        h = hash(key)
        self.seen_keys[h] = self.seen_keys.get(h, 0) + 1
        # Expose counts to the searcher (keyed by the real transposition key).
        count = self.searcher.game_history.get(key, 0)
        self.searcher.game_history[key] = count + 1

    def choose_move(self, fen: str, time_left_ms: int) -> str:
        board = chess.Board(fen)
        legal = list(board.legal_moves)
        if not legal:
            # No legal move: referee should have ended the game, but never crash.
            return "0000"
        legal_sorted = sorted(legal, key=lambda m: m.uci())
        fallback = legal_sorted[0]
        # Prefer a capture of hanging material as the fallback over pure UCI order.
        try:
            fallback = self._quick_fallback(board, legal_sorted)
        except Exception:
            fallback = legal_sorted[0]

        if len(legal_sorted) == 1 or time_left_ms < 20:
            # One reply, or a clock that cannot afford even a shallow search:
            # play the precomputed fallback immediately instead of searching.
            self._track_position(board)
            board.push(fallback)
            self._track_position(board)
            return fallback.uci()

        self._track_position(board)

        budget = allocate_time(time_left_ms, len(legal_sorted))
        clock = Clock()
        clock.start_move(budget)
        # Let iterative deepening use its allocated time while there is a
        # usable clock. A fixed depth ceiling wastes time in positions with
        # few legal moves, especially endings needing long lines. Critically
        # low clocks retain the shallow emergency search.
        max_depth = 4 if time_left_ms < 1200 else 64

        # Single-core CPU root policy move scores + learned position value.
        # One joint inference serves both (see root_policy.evaluate_root).
        policy_scores: dict[chess.Move, float] = {}
        value_cp: float | None = None
        try:
            evaluator = get_root_evaluator()
            if evaluator.is_available():
                policy_scores, value_cp = evaluator.evaluate_root(board, legal_sorted)
        except Exception:
            policy_scores, value_cp = {}, None

        # Sensor fusion: exact material counting beats learned guessing at
        # extremes (bare-board endgames are far from training mass), while
        # the net sees positional nuance the static terms miss near level.
        if value_cp is not None:
            static_cp = float(evaluate(board))
            w_net = 1.0 / (1.0 + math.exp((abs(static_cp) - 300.0) / 150.0))
            static_clip = max(-1200.0, min(1200.0, static_cp))
            value_cp = w_net * value_cp + (1.0 - w_net) * static_clip

        # Uncertainty-based time scaling: when the learned value disagrees
        # with the previous search score the position is contested, so spend
        # more; when they agree, save time. Bounded and never past hard.
        if (
            value_cp is not None
            and self._last_score is not None
            and abs(self._last_score) < MATE_THRESHOLD
            and abs(value_cp) < MATE_THRESHOLD
            and not budget.emergency
        ):
            disagreement = abs(value_cp - float(self._last_score))
            scale = 1.35 if disagreement > 200.0 else (0.9 if disagreement < 50.0 else 1.0)
            if scale != 1.0:
                soft = clock.start + (clock.soft_deadline - clock.start) * scale
                clock.soft_deadline = min(soft, clock.hard_deadline)

        self.searcher.new_search(clock, budget.emergency, root_policy_scores=policy_scores)
        try:
            best, score, pv = self.searcher.iterative_deepening(board, max_depth, fallback)
        except Exception:
            best, score, pv = fallback, -INF, [fallback]
        self._last_score = score

        if best not in legal:
            best = fallback
        # Avoid needless repetition when clearly winning: if our best move
        # repeats a position we have seen twice and we are winning, try the
        # second-best root move from the TT/PV info when available.
        with contextlib.suppress(Exception):
            best = self._avoid_repetition_when_winning(board, legal_sorted, best, score)

        if DEBUG:
            stats = self.searcher.stats
            with contextlib.suppress(Exception):
                print(
                    f"MW d={stats.depth_reached} sd={stats.seldepth} "
                    f"n={stats.nodes} q={stats.qnodes} "
                    f"tt={stats.tt_hits}/{stats.tt_probes} "
                    f"{clock.elapsed_ms():.0f}ms score={score} "
                    f"pv={' '.join(m.uci() for m in pv)}"
                )

        board.push(best)
        self._track_position(board)
        return best.uci()

    def _quick_fallback(self, board: chess.Board, legal_sorted: list[chess.Move]) -> chess.Move:
        # Mate in one if available, else best SEE-ish capture, else first move.
        for move in legal_sorted:
            board.push(move)
            mated = board.is_checkmate()
            board.pop()
            if mated:
                return move
        best: chess.Move | None = None
        best_value = -1
        values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
        }
        for move in legal_sorted:
            if board.is_capture(move):
                target = board.piece_at(move.to_square)
                value = 100
                if target is not None:
                    value = values.get(target.piece_type, 100)
                if move.promotion is not None:
                    value += 800
                if value > best_value:
                    best_value = value
                    best = move
        return best if best is not None else legal_sorted[0]

    def _avoid_repetition_when_winning(
        self,
        board: chess.Board,
        legal_sorted: list[chess.Move],
        best: chess.Move,
        score: int,
    ) -> chess.Move:
        if score < 150 or abs(score) >= MATE_THRESHOLD:
            return best
        if score >= MATE_SCORE - 1000:
            return best
        board.push(best)
        key = board._transposition_key()
        board.pop()
        repeats = self.searcher.game_history.get(key, 0)
        if repeats < 2 and hash(key) not in self.seen_keys:
            return best
        # Seen before and we are winning: pick first non-repeating alternative.
        for alt in legal_sorted:
            if alt == best:
                continue
            board.push(alt)
            akey = board._transposition_key()
            board.pop()
            if self.searcher.game_history.get(akey, 0) < 2:
                return alt
        return best


_ENGINE = MilkyWayEngine()


def get_engine_move(fen: str, time_left_ms: int) -> str:
    return _ENGINE.choose_move(fen, time_left_ms)
