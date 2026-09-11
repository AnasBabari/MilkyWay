"""Generate and verify level-checked opening test banks from master PGNs.

Extracts early opening positions (plies 8-14) from grandmaster PGNs with:
- Equal material (pawns >= 7, equal piece counts)
- King safety and quiescence stability (evaluate == _quiescence)
- Balanced static eval (|eval| <= 25 cp, mean eval near 0)
- Equal colour side-to-move balance (50 White to move, 50 Black to move)
- Equal ECO distribution (20% each of A, B, C, D, E)
- Zero overlap between screen bank and confirm bank
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess  # noqa: E402
import chess.pgn  # noqa: E402

from constants import INF  # noqa: E402
from evaluation import evaluate, evaluate_white_relative  # noqa: E402
from search import Searcher  # noqa: E402
from time_manager import Clock, TimeBudget  # noqa: E402
from tools.test_bank import BankPosition  # noqa: E402
from transposition import TranspositionTable  # noqa: E402


def collect_pool(
    pgn_dir: Path,
    max_games_per_file: int = 800,
) -> dict[str, list[dict[str, Any]]]:
    """Collect candidate opening positions grouped by ECO (A, B, C, D, E)."""
    tt = TranspositionTable(1)
    searcher = Searcher(tt)
    clock = Clock()
    clock.start_move(TimeBudget(soft_ms=10_000_000.0, hard_ms=10_000_000.0, emergency=False))
    searcher.new_search(clock, emergency=False)

    files = sorted(pgn_dir.glob("*.pgn"))
    seen_epd: set[str] = set()
    by_eco: dict[str, list[dict[str, Any]]] = {k: [] for k in ("A", "B", "C", "D", "E")}

    for pgn_path in files:
        with open(pgn_path, encoding="utf-8", errors="ignore") as f:
            game_idx = 0
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                game_idx += 1
                if game_idx > max_games_per_file:
                    break

                eco = game.headers.get("ECO", "A00")
                eco_group = eco[0].upper() if eco and eco[0].upper() in by_eco else "A"

                board = game.board()
                ply = 0
                for move in game.mainline_moves():
                    board.push(move)
                    ply += 1
                    if 8 <= ply <= 14:
                        if board.is_check():
                            continue
                        epd = board.epd()
                        if epd in seen_epd:
                            continue

                        w_pawns = len(board.pieces(chess.PAWN, chess.WHITE))
                        b_pawns = len(board.pieces(chess.PAWN, chess.BLACK))
                        if w_pawns < 7 or b_pawns < 7:
                            continue

                        w_knights = len(board.pieces(chess.KNIGHT, chess.WHITE))
                        b_knights = len(board.pieces(chess.KNIGHT, chess.BLACK))
                        w_bishops = len(board.pieces(chess.BISHOP, chess.WHITE))
                        b_bishops = len(board.pieces(chess.BISHOP, chess.BLACK))
                        w_rooks = len(board.pieces(chess.ROOK, chess.WHITE))
                        b_rooks = len(board.pieces(chess.ROOK, chess.BLACK))
                        w_queens = len(board.pieces(chess.QUEEN, chess.WHITE))
                        b_queens = len(board.pieces(chess.QUEEN, chess.BLACK))

                        # Standard equal trades / equal material
                        if (
                            w_pawns != b_pawns
                            or w_knights != b_knights
                            or w_bishops != b_bishops
                            or w_rooks != b_rooks
                            or w_queens != b_queens
                        ):
                            continue

                        ev = evaluate_white_relative(board)
                        if abs(ev) > 25:
                            continue

                        side_ev = evaluate(board)
                        q_score = searcher._quiescence(board, -INF, INF, 0, 0)
                        if q_score != side_ev:
                            continue

                        seen_epd.add(epd)
                        by_eco[eco_group].append({
                            "fen": board.fen(),
                            "epd": epd,
                            "eval": ev,
                            "ply": ply,
                            "turn": "w" if board.turn == chess.WHITE else "b",
                            "eco": eco,
                            "eco_group": eco_group,
                            "src": pgn_path.stem,
                        })

    return by_eco


def select_balanced_bank(
    by_eco: dict[str, list[dict[str, Any]]],
    count_per_group: int,
    prefix: str,
    used_epds: set[str],
    seed: int,
) -> tuple[list[BankPosition], set[str]]:
    """Select count_per_group * 5 positions balanced in ECO and side-to-move."""
    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []

    # From each ECO group, select count_per_group // 2 White and Black
    n_per_side = count_per_group // 2
    for group in ("A", "B", "C", "D", "E"):
        available_w = [p for p in by_eco[group] if p["epd"] not in used_epds and p["turn"] == "w"]
        available_b = [p for p in by_eco[group] if p["epd"] not in used_epds and p["turn"] == "b"]
        rng.shuffle(available_w)
        rng.shuffle(available_b)

        if len(available_w) < n_per_side:
            raise RuntimeError(
                f"Not enough White-to-move in ECO {group}: {len(available_w)} < {n_per_side}"
            )
        if len(available_b) < n_per_side:
            raise RuntimeError(
                f"Not enough Black-to-move in ECO {group}: {len(available_b)} < {n_per_side}"
            )

        sel_w = available_w[:n_per_side]
        sel_b = available_b[:n_per_side]
        for item in sel_w + sel_b:
            used_epds.add(item["epd"])
            selected.append(item)

    # Deterministic final order
    rng.shuffle(selected)
    bank_positions = [
        BankPosition(
            id=f"{prefix}_{idx + 1:03d}",
            category="opening",
            fen=item["fen"],
            eval_cp=item["eval"],
        )
        for idx, item in enumerate(selected)
    ]
    return bank_positions, used_epds


def write_bank_file(
    path: Path,
    var_name: str,
    positions: list[BankPosition],
    description: str,
) -> None:
    """Write BankPosition tuple to python file."""
    lines = [
        f'"""{description}"""',
        "",
        "from __future__ import annotations",
        "",
        "from tools.test_bank import BankPosition",
        "",
        f"{var_name}: tuple[BankPosition, ...] = (",
    ]
    for p in positions:
        lines.append("    BankPosition(")
        lines.append(f'        "{p.id}", "{p.category}",')
        lines.append(f'        "{p.fen}", {p.eval_cp},')
        lines.append("    ),")
    lines.append(")")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def verify_banks() -> None:
    """Verify levelness, symmetry, stability, and lack of overlap."""
    from tools.confirm_bank import CONFIRM_TEST_BANK
    from tools.screen_bank import SCREEN_TEST_BANK

    print("=== Level Bank Verification Audit ===")
    assert len(SCREEN_TEST_BANK) == 100, f"Screen bank has {len(SCREEN_TEST_BANK)}"
    assert len(CONFIRM_TEST_BANK) == 100, f"Confirm bank has {len(CONFIRM_TEST_BANK)}"

    screen_epds = {chess.Board(p.fen).epd() for p in SCREEN_TEST_BANK}
    confirm_epds = {chess.Board(p.fen).epd() for p in CONFIRM_TEST_BANK}
    assert (
        len(screen_epds) == len(SCREEN_TEST_BANK)
    ), "Duplicate positions detected inside screen_bank!"
    assert (
        len(confirm_epds) == len(CONFIRM_TEST_BANK)
    ), "Duplicate positions detected inside confirm_bank!"
    overlap = screen_epds.intersection(confirm_epds)
    assert not overlap, f"Fatal: found {len(overlap)} overlapping positions!"
    print("[PASS] Disjointness & Uniqueness: 0 overlapping positions, 100 unique per bank.")

    tt = TranspositionTable(1)
    searcher = Searcher(tt)
    clock = Clock()
    clock.start_move(TimeBudget(soft_ms=10_000_000.0, hard_ms=10_000_000.0, emergency=False))
    searcher.new_search(clock, emergency=False)

    for name, bank in (("screen_bank", SCREEN_TEST_BANK), ("confirm_bank", CONFIRM_TEST_BANK)):
        w_turns = 0
        b_turns = 0
        evals: list[int] = []
        w_evals: list[int] = []
        b_evals: list[int] = []
        plies: list[int] = []

        for p in bank:
            board = chess.Board(p.fen)
            assert not board.is_check(), f"Position {p.id} is in check: {p.fen}"
            if board.turn == chess.WHITE:
                w_turns += 1
            else:
                b_turns += 1

            ply = board.fullmove_number * 2 - (1 if board.turn == chess.WHITE else 0)
            plies.append(ply)
            assert 8 <= ply <= 15, f"Position {p.id} ply out of bounds: ply={ply}"

            ev = evaluate_white_relative(board)
            assert abs(ev) <= 30, f"Position {p.id} eval too large: {ev} cp"
            evals.append(ev)
            if board.turn == chess.WHITE:
                w_evals.append(ev)
            else:
                b_evals.append(ev)

            # Quiescence stability
            side_ev = evaluate(board)
            q_score = searcher._quiescence(board, -INF, INF, 0, 0)
            assert q_score == side_ev, f"Position {p.id} unstable: {q_score} != {side_ev}"

            # Equal material check
            w_pawns = len(board.pieces(chess.PAWN, chess.WHITE))
            b_pawns = len(board.pieces(chess.PAWN, chess.BLACK))
            assert w_pawns >= 7 and b_pawns >= 7 and w_pawns == b_pawns, f"Pawns in {p.id}"
            for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
                w_count = len(board.pieces(pt, chess.WHITE))
                b_count = len(board.pieces(pt, chess.BLACK))
                assert w_count == b_count, f"Piece mismatch {pt} in {p.id}"

        mean_eval = sum(evals) / len(evals)
        mean_w = sum(w_evals) / len(w_evals)
        mean_b = sum(b_evals) / len(b_evals)
        colour_bias = abs(mean_w - mean_b)
        assert abs(mean_w) <= 10.0, f"White-to-move mean eval exceeds threshold: {mean_w:+.2f} cp"
        assert abs(mean_b) <= 10.0, f"Black-to-move mean eval exceeds threshold: {mean_b:+.2f} cp"
        assert colour_bias <= 10.0, f"Colour bias exceeds threshold: {colour_bias:.2f} cp"
        print(
            f"[PASS] {name}: 100 positions, turn={w_turns}W/{b_turns}B, "
            f"mean eval={mean_eval:+.2f} cp (W: {mean_w:+.2f}, B: {mean_b:+.2f}, "
            f"bias: {colour_bias:.2f} cp), "
            f"plies={min(plies)}-{max(plies)}, all 100% quiescence stable."
        )

    print("All level-bank quality gates passed successfully!\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify bank files")
    parser.add_argument("--seed", type=int, default=20260906, help="Random seed")
    args = parser.parse_args()

    if args.verify:
        verify_banks()
        return

    print("Extracting candidate positions from master PGNs...")
    by_eco = collect_pool(ROOT / "training" / "data" / "raw_pgn")
    for group, items in by_eco.items():
        w_c = sum(1 for x in items if x["turn"] == "w")
        b_c = sum(1 for x in items if x["turn"] == "b")
        print(f"  ECO {group}: {len(items)} pool candidates ({w_c} W, {b_c} B)")

    used_epds: set[str] = set()
    print("Selecting 100 balanced positions for screen_bank...")
    screen_bank, used_epds = select_balanced_bank(
        by_eco, count_per_group=20, prefix="sbank", used_epds=used_epds, seed=args.seed
    )

    print("Selecting 100 independent positions for confirm_bank...")
    confirm_bank, used_epds = select_balanced_bank(
        by_eco, count_per_group=20, prefix="cbank", used_epds=used_epds, seed=args.seed + 1
    )

    screen_file = ROOT / "tools" / "screen_bank.py"
    confirm_file = ROOT / "tools" / "confirm_bank.py"

    write_bank_file(
        screen_file,
        "SCREEN_TEST_BANK",
        screen_bank,
        "Screen opening test bank: 100 level, quiescence-stable opening positions (plies 8-14).",
    )
    print(f"Wrote {len(screen_bank)} positions to {screen_file}")

    write_bank_file(
        confirm_file,
        "CONFIRM_TEST_BANK",
        confirm_bank,
        "Confirmation opening test bank: 100 independent level opening positions (plies 8-14).",
    )
    print(f"Wrote {len(confirm_bank)} positions to {confirm_file}")

    print("\nRunning immediate verification...")
    verify_banks()


if __name__ == "__main__":
    main()
