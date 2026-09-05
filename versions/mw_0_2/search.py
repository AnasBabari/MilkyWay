"""MilkyWay search: iterative deepening, PVS alpha-beta, quiescence, pruning."""

from __future__ import annotations

from collections.abc import Hashable

import chess

from constants import (
    DRAW_SCORE,
    EXACT,
    INF,
    LOWER,
    MATE_SCORE,
    MAX_PLY,
    MAX_QPLY,
    UPPER,
)
from engine_types import SearchStats, SearchTimeout
from evaluation import evaluate
from move_ordering import capture_mvv_lva, order_moves
from time_manager import Clock
from transposition import TranspositionTable

MATE_THRESHOLD: int = MATE_SCORE - MAX_PLY - 16
FUTILITY_MARGIN: tuple[int, ...] = (0, 150, 300)
RF_MARGIN: int = 120
ASPIRATION_START: int = 30
NULL_MIN_DEPTH: int = 3
LMR_MIN_DEPTH: int = 3
LMR_MOVE_INDEX: int = 4


def _to_tt(score: int, ply: int) -> int:
    if score >= MATE_THRESHOLD:
        return score + ply
    if score <= -MATE_THRESHOLD:
        return score - ply
    return score


def _from_tt(score: int, ply: int) -> int:
    if score >= MATE_THRESHOLD:
        return score - ply
    if score <= -MATE_THRESHOLD:
        return score + ply
    return score


class Searcher:
    """Stateful searcher. TT/history/killers persist across moves in a game."""

    def __init__(self, tt: TranspositionTable) -> None:
        self.tt = tt
        self.killers: list[list[chess.Move | None]] = [[None, None] for _ in range(MAX_PLY + 8)]
        self.history: list[list[list[int]]] = [
            [[0 for _ in range(64)] for _ in range(64)] for _ in range(2)
        ]
        self.stats = SearchStats()
        self.clock = Clock()
        self.game_history: dict[Hashable, int] = {}
        self._stack_keys: list[Hashable] = []
        self._emergency = False

    def new_game(self) -> None:
        self.tt.clear()
        self.killers = [[None, None] for _ in range(MAX_PLY + 8)]
        self.history = [[[0 for _ in range(64)] for _ in range(64)] for _ in range(2)]
        self.game_history.clear()

    def new_search(self, clock: Clock, emergency: bool) -> None:
        self.clock = clock
        self._emergency = emergency
        self.stats = SearchStats()
        self._stack_keys = []
        self.tt.new_generation()

    # -- public -----------------------------------------------------------
    def iterative_deepening(
        self,
        board: chess.Board,
        max_depth: int,
        fallback: chess.Move,
    ) -> tuple[chess.Move, int, list[chess.Move]]:
        best_move = fallback
        best_score = -INF
        best_pv: list[chess.Move] = [fallback]
        # Depth 1 first without aspiration so we always have something.
        prev_score: int | None = None
        for depth in range(1, max_depth + 1):
            try:
                if prev_score is None or depth < 4 or abs(prev_score) >= MATE_THRESHOLD:
                    score, pv = self._search_root(board, depth, -INF, INF)
                else:
                    window = ASPIRATION_START + depth * 4
                    alpha = prev_score - window
                    beta = prev_score + window
                    score, pv = self._search_root(board, depth, alpha, beta)
                    if score <= alpha:
                        score, pv = self._search_root(board, depth, -INF, beta)
                    elif score >= beta:
                        score, pv = self._search_root(board, depth, alpha, INF)
            except SearchTimeout:
                break
            if pv:
                best_move = pv[0]
                best_pv = pv
                best_score = score
            else:
                # No PV but no timeout: keep move, update score.
                best_score = score
            prev_score = best_score
            self.stats.depth_reached = depth
            self.stats.score = best_score
            self.stats.pv = [m.uci() for m in best_pv]
            if self.clock.past_soft():
                break
            # Found forced mate at minimal depth: no need to go deeper.
            if best_score >= MATE_THRESHOLD and depth >= 3:
                break
            if self._emergency and depth >= 4:
                break
        return best_move, best_score, best_pv

    # -- root -------------------------------------------------------------
    def _search_root(
        self, board: chess.Board, depth: int, alpha: int, beta: int
    ) -> tuple[int, list[chess.Move]]:
        key = board._transposition_key()
        self._poll_timeout()
        legal = list(board.legal_moves)
        if not legal:
            if board.is_check():
                return -MATE_SCORE, []
            return DRAW_SCORE, []
        tt_entry = self.tt.probe(key)
        self.stats.tt_probes += 1
        tt_move: chess.Move | None = None
        if tt_entry is not None:
            self.stats.tt_hits += 1
            tt_move = tt_entry.best_move
        ordered = order_moves(board, legal, tt_move, (None, None), self.history)
        best_score = -INF
        best_move: chess.Move | None = None
        pv: list[chess.Move] = []
        child_pvs: dict[str, list[chess.Move]] = {}
        alpha_orig = alpha
        for index, move in enumerate(ordered):
            board.push(move)
            self._stack_keys.append(board._transposition_key())
            try:
                if index == 0:
                    score = -self._negamax(board, depth - 1, -beta, -alpha, 1, True, child_pvs)
                else:
                    # PVS null window.
                    score = -self._negamax(board, depth - 1, -alpha - 1, -alpha, 1, True, child_pvs)
                    if alpha < score < beta:
                        score = -self._negamax(board, depth - 1, -beta, -alpha, 1, True, child_pvs)
            finally:
                self._stack_keys.pop()
                board.pop()
            if score > best_score:
                best_score = score
                best_move = move
                child = child_pvs.get(move.uci(), [])
                pv = [move, *child]
            if score > alpha:
                alpha = score
            if alpha >= beta:
                self.stats.beta_cutoffs += 1
                self._record_cutoff(board.turn, move, board, depth)
                break
        bound = EXACT
        if best_score <= alpha_orig:
            bound = UPPER
        elif best_score >= beta:
            bound = LOWER
        self.tt.store(key, depth, _to_tt(best_score, 0), bound, best_move)
        if best_move is None:
            return best_score, []
        return best_score, pv

    # -- negamax ----------------------------------------------------------
    def _negamax(
        self,
        board: chess.Board,
        depth: int,
        alpha: int,
        beta: int,
        ply: int,
        can_null: bool,
        child_pvs: dict[str, list[chess.Move]],
    ) -> int:
        self.stats.nodes += 1
        if ply > self.stats.seldepth:
            self.stats.seldepth = ply
        # Poll the hard deadline more often in emergency, when the budget is
        # small enough that 256 nodes of overshoot could flag the game.
        if (self.stats.nodes & (63 if self._emergency else 255)) == 0:
            self._poll_timeout()
        if ply >= MAX_PLY:
            return evaluate(board)

        key = board._transposition_key()
        # Repetition / fifty-move / insufficient material.
        rep = self.game_history.get(key, 0) + sum(1 for k in self._stack_keys if k == key)
        if rep >= 2:
            return DRAW_SCORE
        if board.is_fifty_moves() or board.is_insufficient_material():
            return DRAW_SCORE

        in_check = board.is_check()
        # Check extension (limited, not in emergency).
        if in_check and depth < MAX_PLY - 1 and not self._emergency:
            depth += 1

        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply, 0)

        # TT probe.
        tt_move: chess.Move | None = None
        tt_entry = self.tt.probe(key)
        self.stats.tt_probes += 1
        if tt_entry is not None:
            self.stats.tt_hits += 1
            tt_move = tt_entry.best_move
            if tt_entry.depth >= depth:
                tt_score = _from_tt(tt_entry.score, ply)
                if tt_entry.bound == EXACT:
                    self.stats.tt_cutoffs += 1
                    return tt_score
                if tt_entry.bound == LOWER and tt_score >= beta:
                    self.stats.tt_cutoffs += 1
                    return tt_score
                if tt_entry.bound == UPPER and tt_score <= alpha:
                    self.stats.tt_cutoffs += 1
                    return tt_score

        static = evaluate(board)

        # Reverse futility: clearly above beta at low depth.
        if (
            not in_check
            and depth <= 3
            and static - RF_MARGIN * depth >= beta
            and abs(beta) < MATE_THRESHOLD
        ):
            return static

        # Null-move pruning (conservative).
        if (
            can_null
            and not in_check
            and depth >= NULL_MIN_DEPTH
            and static >= beta
            and abs(beta) < MATE_THRESHOLD
            and self._has_non_pawn_material(board)
            and not self._emergency
        ):
            board.push(chess.Move.null())
            self._stack_keys.append(board._transposition_key())
            try:
                reduction = 2 + (1 if depth > 5 else 0)
                null_score = -self._negamax(
                    board, depth - 1 - reduction, -beta, -beta + 1, ply + 1, False, {}
                )
            finally:
                self._stack_keys.pop()
                board.pop()
            if null_score >= beta:
                self.stats.null_cutoffs += 1
                return null_score

        legal = list(board.legal_moves)
        if not legal:
            if in_check:
                return -MATE_SCORE + ply
            return DRAW_SCORE

        # Futility pruning setup (shallow, not in check, no mate in window).
        futile = (
            not in_check
            and depth <= 2
            and abs(alpha) < MATE_THRESHOLD
            and abs(beta) < MATE_THRESHOLD
        )
        fut_margin = FUTILITY_MARGIN[depth] if depth < len(FUTILITY_MARGIN) else 300
        killers = (
            (self.killers[ply][0], self.killers[ply][1])
            if ply < len(self.killers)
            else (None, None)
        )
        ordered = order_moves(board, legal, tt_move, killers, self.history)

        best_score = -INF
        best_move: chess.Move | None = None
        alpha_orig = alpha
        for index, move in enumerate(ordered):
            tactical = board.is_capture(move) or move.promotion is not None
            # Futility: skip late quiet moves that cannot raise alpha.
            if futile and index > 0 and not tactical:
                gives_check_quick = False
                # Quiet checks are never futile-pruned (need push to know).
                board.push(move)
                gives_check_quick = board.is_check()
                board.pop()
                if not gives_check_quick and static + fut_margin <= alpha:
                    continue
            board.push(move)
            self._stack_keys.append(board._transposition_key())
            try:
                if index == 0:
                    score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1, True, {})
                else:
                    # LMR: late quiet moves get reduced depth first.
                    reduced = depth - 1
                    do_lmr = (
                        not self._emergency
                        and depth >= LMR_MIN_DEPTH
                        and index >= LMR_MOVE_INDEX
                        and not tactical
                        and not in_check
                    )
                    if do_lmr:
                        reduced = depth - 2
                        if depth > 5 and index > 10:
                            reduced = depth - 3
                        reduced = max(1, reduced)
                        score = -self._negamax(
                            board, reduced, -alpha - 1, -alpha, ply + 1, True, {}
                        )
                        if score > alpha:
                            self.stats.lmr_researches += 1
                            score = -self._negamax(
                                board, depth - 1, -alpha - 1, -alpha, ply + 1, True, {}
                            )
                    else:
                        score = -self._negamax(
                            board, depth - 1, -alpha - 1, -alpha, ply + 1, True, {}
                        )
                    if alpha < score < beta:
                        score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1, True, {})
            finally:
                self._stack_keys.pop()
                board.pop()
            # Store child PV line for the root caller if this node is a root child.
            # (Root passes its own dict; deeper nodes use throwaway dicts.)
            if move.uci() not in child_pvs and ply == 1:
                # Reconstruct shallowly: we don't keep full lines below root
                # children to save overhead; root PV is [move] + best reply if
                # available from TT on the next iteration.
                child_pvs[move.uci()] = []
            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score
            if alpha >= beta:
                self.stats.beta_cutoffs += 1
                mover = board.turn
                self._record_cutoff(mover, move, board, depth)
                break

        bound = EXACT
        if best_score <= alpha_orig:
            bound = UPPER
        elif best_score >= beta:
            bound = LOWER
        self.tt.store(key, depth, _to_tt(best_score, ply), bound, best_move)
        return best_score

    # -- quiescence -------------------------------------------------------
    def _quiescence(self, board: chess.Board, alpha: int, beta: int, ply: int, qply: int) -> int:
        self.stats.qnodes += 1
        if ply > self.stats.seldepth:
            self.stats.seldepth = ply
        if (self.stats.qnodes & (63 if self._emergency else 255)) == 0:
            self._poll_timeout()

        key = board._transposition_key()
        rep = self.game_history.get(key, 0) + sum(1 for k in self._stack_keys if k == key)
        if rep >= 2:
            return DRAW_SCORE
        if board.is_fifty_moves() or board.is_insufficient_material():
            return DRAW_SCORE

        in_check = board.is_check()
        if in_check:
            if qply >= MAX_QPLY or ply >= MAX_PLY:
                return evaluate(board)
            legal = list(board.legal_moves)
            if not legal:
                return -MATE_SCORE + ply
            ordered = order_moves(board, legal, None, (None, None), self.history)
            best = -INF
            for move in ordered:
                board.push(move)
                self._stack_keys.append(board._transposition_key())
                try:
                    score = -self._quiescence(board, -beta, -alpha, ply + 1, qply + 1)
                finally:
                    self._stack_keys.pop()
                    board.pop()
                if score > best:
                    best = score
                if score > alpha:
                    alpha = score
                if alpha >= beta:
                    break
            return best

        stand_pat = evaluate(board)
        if stand_pat >= beta:
            return stand_pat
        if stand_pat > alpha:
            alpha = stand_pat
        if qply >= MAX_QPLY or ply >= MAX_PLY:
            return alpha

        captures: list[chess.Move] = [
            m for m in board.legal_moves if board.is_capture(m) or m.promotion is not None
        ]
        if not captures:
            return alpha
        # Order captures by MVV-LVA (deterministic).
        captures.sort(key=lambda m: (-capture_mvv_lva(board, m), m.uci()))
        qcap_limit = 4 if self._emergency else len(captures)
        for move in captures[:qcap_limit]:
            # Delta pruning: capture cannot raise alpha even with a bonus.
            if not self._emergency and move.promotion is None:
                if board.is_en_passant(move):
                    victim_value = 100
                else:
                    target = board.piece_at(move.to_square)
                    victim_value = {1: 100, 2: 320, 3: 330, 4: 500, 5: 900}.get(
                        target.piece_type if target else 0, 0
                    )
                if stand_pat + victim_value + 150 < alpha:
                    continue
            board.push(move)
            self._stack_keys.append(board._transposition_key())
            try:
                score = -self._quiescence(board, -beta, -alpha, ply + 1, qply + 1)
            finally:
                self._stack_keys.pop()
                board.pop()
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        return alpha

    # -- helpers ----------------------------------------------------------
    def _poll_timeout(self) -> None:
        if self.clock.past_hard():
            raise SearchTimeout

    def _has_non_pawn_material(self, board: chess.Board) -> bool:
        color = board.turn
        return bool(
            board.pieces(chess.KNIGHT, color)
            or board.pieces(chess.BISHOP, color)
            or board.pieces(chess.ROOK, color)
            or board.pieces(chess.QUEEN, color)
        )

    def _record_cutoff(
        self, mover: chess.Color, move: chess.Move, board: chess.Board, depth: int
    ) -> None:
        # Only quiet moves earn killer/history credit.
        if board.is_capture(move) or move.promotion is not None:
            return
        if move.uci() == "0000":
            return
        stm = 1 if mover == chess.WHITE else 0
        bonus = depth * depth
        cell = self.history[stm][move.from_square][move.to_square]
        self.history[stm][move.from_square][move.to_square] = min(cell + bonus, 100000)
        # Age other entries occasionally to keep history bounded.
        if cell + bonus >= 100000:
            for c in (0, 1):
                for f in range(64):
                    row = self.history[c][f]
                    for t in range(64):
                        row[t] //= 2
        ply = min(len(self.killers) - 1, max(0, len(self._stack_keys)))
        slot = self.killers[ply]
        if slot[0] != move:
            slot[1] = slot[0]
            slot[0] = move
