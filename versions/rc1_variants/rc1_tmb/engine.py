"""MilkyWay persistent engine: game history, time control, search orchestration."""

from __future__ import annotations

import contextlib

import chess

from constants import INF, MATE_SCORE
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

    def reset_game(self) -> None:
        self.searcher.new_game()
        self.seen_keys.clear()
        self.last_fen = None

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
        # Depth cap: emergency searches stay shallow.
        max_depth = 4 if budget.emergency else 64
        if time_left_ms < 6000:
            max_depth = min(max_depth, 6 if not budget.emergency else 4)

        # Single-core CPU root policy move scores
        policy_scores: dict[chess.Move, float] = {}
        try:
            evaluator = get_root_evaluator()
            if evaluator.is_available():
                policy_scores = evaluator.get_move_scores(board, legal_sorted)
        except Exception:
            policy_scores = {}

        self.searcher.new_search(clock, budget.emergency, root_policy_scores=policy_scores)
        try:
            best, score, pv = self.searcher.iterative_deepening(board, max_depth, fallback)
        except Exception:
            best, score, pv = fallback, -INF, [fallback]

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
