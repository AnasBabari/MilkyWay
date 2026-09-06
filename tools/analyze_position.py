"""Diagnostic position analyzer for MilkyWay: root moves, PVs, stats, and search ablations."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess  # noqa: E402

from constants import (  # noqa: E402
    DRAW_SCORE,
    EXACT,
    INF,
    LOWER,
    MATE_SCORE,
    MAX_PLY,
    UPPER,
)
from engine_types import SearchTimeout  # noqa: E402
from evaluation import evaluate  # noqa: E402
from move_ordering import order_moves  # noqa: E402
from search import (  # noqa: E402
    ASPIRATION_START,
    FUTILITY_MARGIN,
    LMR_MIN_DEPTH,
    LMR_MOVE_INDEX,
    MATE_THRESHOLD,
    NULL_MIN_DEPTH,
    RF_MARGIN,
    Searcher,
    _from_tt,
    _to_tt,
)
from time_manager import Clock, TimeBudget, allocate_time  # noqa: E402
from transposition import TranspositionTable  # noqa: E402

DEFAULT_CRITICAL_FEN = "1rBq1r2/1p3p1k/2n3pb/p1p4p/P3Pp1P/3P2P1/1PPQ1P2/R2R2K1 w - - 0 19"
ROUND20_MATE_FEN = "1r3r2/1p5k/2np2pb/p1p5/P3P1qP/2NP1p2/1PPQ1P1K/R2R4 w - - 0 23"


@dataclass
class RootMoveResult:
    move: chess.Move
    score: int
    pv: list[chess.Move]
    nodes: int
    qnodes: int


class DiagnosticSearcher(Searcher):
    """Searcher with toggles for search ablations and deep PV tracking."""

    def __init__(
        self,
        tt: TranspositionTable,
        enable_tt: bool = True,
        enable_lmr: bool = True,
        enable_null: bool = True,
        enable_futility: bool = True,
        enable_aspiration: bool = True,
        enable_rf: bool = True,
    ) -> None:
        super().__init__(tt)
        self.enable_tt = enable_tt
        self.enable_lmr = enable_lmr
        self.enable_null = enable_null
        self.enable_futility = enable_futility
        self.enable_aspiration = enable_aspiration
        self.enable_rf = enable_rf

    def iterative_deepening(
        self,
        board: chess.Board,
        max_depth: int,
        fallback: chess.Move,
    ) -> tuple[chess.Move, int, list[chess.Move]]:
        best_move = fallback
        best_score = -INF
        best_pv: list[chess.Move] = [fallback]
        prev_score: int | None = None

        for depth in range(1, max_depth + 1):
            try:
                if (
                    not self.enable_aspiration
                    or prev_score is None
                    or depth < 4
                    or abs(prev_score) >= MATE_THRESHOLD
                ):
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
                best_score = score

            prev_score = best_score
            self.stats.depth_reached = depth
            self.stats.score = best_score
            self.stats.pv = [m.uci() for m in best_pv]

            if self.clock.past_soft():
                break
            if best_score >= MATE_THRESHOLD and depth >= 3:
                break
            if self._emergency and depth >= 4:
                break

        return best_move, best_score, best_pv

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
        if (self.stats.nodes & (63 if self._emergency else 255)) == 0:
            self._poll_timeout()
        if ply >= MAX_PLY:
            return evaluate(board)

        key = board._transposition_key()
        rep = self.game_history.get(key, 0) + sum(1 for k in self._stack_keys if k == key)
        if rep >= 2:
            return DRAW_SCORE
        if board.is_fifty_moves() or board.is_insufficient_material():
            return DRAW_SCORE

        in_check = board.is_check()
        if in_check and depth < MAX_PLY - 1 and not self._emergency:
            depth += 1

        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply, 0)

        tt_move: chess.Move | None = None
        if self.enable_tt:
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

        if (
            self.enable_rf
            and not in_check
            and depth <= 3
            and static - RF_MARGIN * depth >= beta
            and abs(beta) < MATE_THRESHOLD
        ):
            return static

        if (
            self.enable_null
            and can_null
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

        futile = (
            self.enable_futility
            and not in_check
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
            if futile and index > 0 and not tactical:
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
                    reduced = depth - 1
                    do_lmr = (
                        self.enable_lmr
                        and not self._emergency
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
        if self.enable_tt:
            self.tt.store(key, depth, _to_tt(best_score, ply), bound, best_move)
        return best_score

    def extract_pv(self, board: chess.Board, max_len: int = 8) -> list[chess.Move]:
        """Reconstruct PV line using TT entries."""
        pv: list[chess.Move] = []
        curr = board.copy()
        for _ in range(max_len):
            key = curr._transposition_key()
            entry = self.tt.probe(key)
            if entry and entry.best_move and entry.best_move in curr.legal_moves:
                pv.append(entry.best_move)
                curr.push(entry.best_move)
            else:
                break
        return pv


def analyze_all_root_moves(
    board: chess.Board,
    depth: int,
    searcher: DiagnosticSearcher,
) -> list[RootMoveResult]:
    """Search every legal root move independently at full window to get accurate scores."""
    legal = list(board.legal_moves)
    results: list[RootMoveResult] = []

    tt_entry = searcher.tt.probe(board._transposition_key())
    tt_move = tt_entry.best_move if tt_entry else None
    ordered = order_moves(board, legal, tt_move, (None, None), searcher.history)

    if searcher.clock.hard_deadline <= 0:
        searcher.clock.start_move(
            TimeBudget(soft_ms=1000000.0, hard_ms=1000000.0, emergency=False)
        )

    for m in ordered:
        n_before = searcher.stats.nodes
        qn_before = searcher.stats.qnodes
        board.push(m)
        searcher._stack_keys.append(board._transposition_key())
        try:
            score = -searcher._negamax(board, depth - 1, -INF, INF, 1, True, {})
        finally:
            searcher._stack_keys.pop()
            board.pop()

        board.push(m)
        cont = searcher.extract_pv(board, max_len=depth - 1)
        board.pop()
        pv = [m, *cont]

        results.append(
            RootMoveResult(
                move=m,
                score=score,
                pv=pv,
                nodes=searcher.stats.nodes - n_before,
                qnodes=searcher.stats.qnodes - qn_before,
            )
        )

    results.sort(key=lambda r: (-r.score, r.move.uci()))
    return results


def run_ablation_matrix(board: chess.Board, depth: int) -> None:
    """Compare search configurations across standard ablations."""
    configs: list[tuple[str, dict[str, bool]]] = [
        ("1. Production (Full MW-0.2)", {}),
        ("2. No TT", {"enable_tt": False}),
        ("3. No LMR", {"enable_lmr": False}),
        ("4. No Null Move", {"enable_null": False}),
        ("5. No Futility", {"enable_futility": False}),
        ("6. No Reverse Futility", {"enable_rf": False}),
        ("7. No Aspiration", {"enable_aspiration": False}),
        (
            "8. Conservative Alpha-Beta",
            {
                "enable_lmr": False,
                "enable_null": False,
                "enable_futility": False,
                "enable_rf": False,
            },
        ),
        (
            "9. Pure Minimax",
            {
                "enable_tt": False,
                "enable_lmr": False,
                "enable_null": False,
                "enable_futility": False,
                "enable_rf": False,
                "enable_aspiration": False,
            },
        ),
    ]

    print(f"\n{'='*75}")
    print(f"SEARCH ABLATION MATRIX (Depth {depth})")
    print(f"{'='*75}")
    hdr = f"{'Configuration':<30} | {'Best Move':<9} | {'Score':<7} | {'Nodes':<8} | {'QNodes':<8}"
    print(hdr)
    print("-" * len(hdr))

    for name, kwargs in configs:
        tt = TranspositionTable(16)
        s = DiagnosticSearcher(tt, **kwargs)
        clock = Clock()
        clock.start_move(TimeBudget(soft_ms=1000000.0, hard_ms=1000000.0, emergency=False))
        s.new_search(clock, emergency=False)
        score, pv = s._search_root(board, depth, -INF, INF)
        best_uci = pv[0].uci() if pv else "none"
        print(
            f"{name:<30} | {best_uci:<9} | {score:<+7d} | {s.stats.nodes:<8d} | "
            f"{s.stats.qnodes:<8d}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MilkyWay Position Analyzer & Search Ablation Tool"
    )
    parser.add_argument("--fen", type=str, default=DEFAULT_CRITICAL_FEN, help="FEN string")
    parser.add_argument("--depth", type=int, default=5, help="Search depth")
    parser.add_argument("--time-ms", type=int, default=None, help="Timed budget ms")
    parser.add_argument("--all-root-moves", action="store_true", help="Rank all legal root moves")
    parser.add_argument("--ablation-matrix", action="store_true", help="Run ablation matrix")
    parser.add_argument("--no-tt", action="store_true", help="Disable TT")
    parser.add_argument("--no-lmr", action="store_true", help="Disable LMR")
    parser.add_argument("--no-null", action="store_true", help="Disable Null Move")
    parser.add_argument("--no-futility", action="store_true", help="Disable Futility")
    parser.add_argument("--no-rf", action="store_true", help="Disable Reverse Futility")
    parser.add_argument("--no-aspiration", action="store_true", help="Disable Aspiration")
    parser.add_argument("--no-pruning", action="store_true", help="Disable all pruning")
    args = parser.parse_args()

    board = chess.Board(args.fen)
    print(f"Position: {board.fen()}")
    print(f"Side to move: {'White' if board.turn == chess.WHITE else 'Black'}")
    print(f"Static evaluation: {evaluate(board):+d} cp")

    if args.ablation_matrix:
        run_ablation_matrix(board, args.depth)
        return

    enable_tt = not args.no_tt
    enable_lmr = not (args.no_lmr or args.no_pruning)
    enable_null = not (args.no_null or args.no_pruning)
    enable_futility = not (args.no_futility or args.no_pruning)
    enable_rf = not (args.no_rf or args.no_pruning)
    enable_aspiration = not args.no_aspiration

    tt = TranspositionTable(16)
    searcher = DiagnosticSearcher(
        tt,
        enable_tt=enable_tt,
        enable_lmr=enable_lmr,
        enable_null=enable_null,
        enable_futility=enable_futility,
        enable_aspiration=enable_aspiration,
        enable_rf=enable_rf,
    )

    if args.time_ms is not None:
        budget = allocate_time(args.time_ms, len(list(board.legal_moves)), increment_ms=500)
        clock = Clock()
        clock.start_move(budget)
        searcher.new_search(clock, emergency=budget.emergency)
        fallback = next(iter(board.legal_moves))
        t0 = time.monotonic()
        timed_best_m, timed_best_s, timed_best_pv = searcher.iterative_deepening(
            board, max_depth=args.depth, fallback=fallback
        )
        el = time.monotonic() - t0
        print(f"\nTimed Search ({args.time_ms} ms budget):")
        print(f"  Best move      : {timed_best_m.uci()} ({board.san(timed_best_m)})")
        print(f"  Score          : {timed_best_s:+d} cp")
        print(f"  Depth completed: {searcher.stats.depth_reached}")
        print(f"  Seldepth       : {searcher.stats.seldepth}")
        print(f"  Nodes          : {searcher.stats.nodes:,} (QNodes: {searcher.stats.qnodes:,})")
        print(f"  Time           : {el*1000:.1f} ms")
        print(f"  PV             : {' '.join(m.uci() for m in timed_best_pv)}")
    else:
        clock = Clock()
        clock.start_move(TimeBudget(soft_ms=1000000.0, hard_ms=1000000.0, emergency=False))
        searcher.new_search(clock, emergency=False)
        t0 = time.monotonic()
        best_s, best_pv = searcher._search_root(board, args.depth, -INF, INF)
        el = time.monotonic() - t0
        fixed_best_m: chess.Move | None = best_pv[0] if best_pv else None
        print(f"\nFixed-Depth Search (Depth {args.depth}):")
        if fixed_best_m:
            print(f"  Best move      : {fixed_best_m.uci()} ({board.san(fixed_best_m)})")
        print(f"  Score          : {best_s:+d} cp")
        print(f"  Seldepth       : {searcher.stats.seldepth}")
        print(f"  Nodes          : {searcher.stats.nodes:,} (QNodes: {searcher.stats.qnodes:,})")
        print(f"  Time           : {el*1000:.1f} ms")
        print(
            f"  TT Probes/Hits : {searcher.stats.tt_probes:,} / {searcher.stats.tt_hits:,} "
            f"(Cutoffs: {searcher.stats.tt_cutoffs:,})"
        )
        print(f"  Beta Cutoffs   : {searcher.stats.beta_cutoffs:,}")
        print(f"  Null Cutoffs   : {searcher.stats.null_cutoffs:,}")
        print(f"  LMR Researches : {searcher.stats.lmr_researches:,}")
        if best_pv:
            full_pv = [best_pv[0], *searcher.extract_pv(board, max_len=args.depth - 1)]
            print(f"  PV             : {' '.join(m.uci() for m in full_pv)}")

    if args.all_root_moves:
        print(f"\n{'='*75}")
        print(f"ALL ROOT MOVES EVALUATION (Depth {args.depth})")
        print(f"{'='*75}")
        print(f"{'#':<3} | {'Move':<7} | {'SAN':<8} | {'Score':<7} | {'Nodes':<7} | {'PV Line'}")
        print(f"{'-'*3}-|-{'-'*7}-|-{'-'*8}-|-{'-'*7}-|-{'-'*7}-|-{'-'*35}")
        results = analyze_all_root_moves(board, args.depth, searcher)
        for idx, r in enumerate(results, 1):
            san = board.san(r.move)
            pv_str = " ".join(m.uci() for m in r.pv)
            print(
                f"{idx:<3d} | {r.move.uci():<7} | {san:<8} | {r.score:<+7d} | "
                f"{r.nodes:<7d} | {pv_str}"
            )


if __name__ == "__main__":
    main()
