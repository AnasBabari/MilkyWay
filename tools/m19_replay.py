"""Replay positions from 120s+0.5s M18 bridge to test the depth horizon hypothesis."""

from __future__ import annotations

import importlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.test_bank import PAIRED_TEST_BANK  # noqa: E402


@dataclass
class PositionDecisionTrace:
    pos_id: str
    fen: str
    move_num: int
    clock_ms: int
    engine_label: str
    soft_ms: float
    hard_ms: float
    actual_ms: float
    depth_reached: int
    nodes: int
    score: int
    move: str
    pv: str


def run_engine_decision(
    engine_dir: Path,
    fen: str,
    clock_ms: int,
    engine_label: str,
) -> PositionDecisionTrace:
    engine_dir_str = str(engine_dir.resolve())
    sys.path.insert(0, engine_dir_str)

    modules = (
        "agent", "engine", "search", "time_manager",
        "move_ordering", "evaluation", "root_policy",
    )
    for mod in modules:
        if mod in sys.modules:
            del sys.modules[mod]

    engine_mod = importlib.import_module('engine')
    time_manager_mod = importlib.import_module('time_manager')

    eng = engine_mod.MilkyWayEngine()
    board = chess.Board(fen)
    legal_count = len(list(board.legal_moves))
    budget = time_manager_mod.allocate_time(clock_ms, legal_count, increment_ms=500)

    t0 = time.perf_counter()
    move_uci = eng.choose_move(fen, clock_ms)
    actual_ms = (time.perf_counter() - t0) * 1000.0

    stats = eng.searcher.stats
    pv_str = " ".join(m.uci() if hasattr(m, "uci") else str(m) for m in stats.pv[:5])

    if sys.path[0] == engine_dir_str:
        sys.path.pop(0)

    return PositionDecisionTrace(
        pos_id='',
        fen=fen,
        move_num=board.fullmove_number,
        clock_ms=clock_ms,
        engine_label=engine_label,
        soft_ms=budget.soft_ms,
        hard_ms=budget.hard_ms,
        actual_ms=actual_ms,
        depth_reached=stats.depth_reached,
        nodes=stats.nodes,
        score=stats.score,
        move=move_uci,
        pv=pv_str,
    )



def main() -> None:
    full_pairs_path = ROOT / "experiments" / "m18" / "full_pairs.json"
    if not full_pairs_path.exists():
        print(f"Error: {full_pairs_path} not found.")
        sys.exit(1)

    with open(full_pairs_path, encoding='utf-8') as f:
        pairs_data = json.load(f)

    bank_map = {p.id: p for p in PAIRED_TEST_BANK}
    test_fens: list[tuple[str, str]] = []
    for item in pairs_data:
        pos_id = item['pos_id']
        if pos_id in bank_map:
            test_fens.append((pos_id, bank_map[pos_id].fen))

    rc1_dir = ROOT
    m19a_dir = ROOT / "versions" / "rc1_variants" / "rc1_tma"
    mw02_dir = ROOT / "versions" / "mw_0_2"

    print(f'Loaded {len(test_fens)} positions from 120s bridge.')
    print('Testing clock regimes: Move 15 (90s), Move 30 (45s), Move 50 (15s)...')

    results: list[dict[str, object]] = []

    clock_regimes = [
        ('move_15', 90000),
        ('move_30', 45000),
        ('move_50', 15000),
    ]

    for pos_id, fen in test_fens[:6]:
        print(f'\n--- Position {pos_id} ---')
        for regime_name, clock_ms in clock_regimes:
            print(f'  Regime {regime_name} ({clock_ms}ms):')
            engines = [
                ("RC1 (TM-B)", rc1_dir),
                ("M19-A (TM-A)", m19a_dir),
                ("MW-0.2 (TM-A)", mw02_dir),
            ]
            for label, edir in engines:
                trace = run_engine_decision(edir, fen, clock_ms, label)
                trace.pos_id = pos_id
                results.append(asdict(trace))
                print(
                    f"    {label:<14}: soft={trace.soft_ms:>5.0f}ms, "
                    f"actual={trace.actual_ms:>5.0f}ms, "
                    f"depth={trace.depth_reached:>2}, nodes={trace.nodes:>6}, "
                    f"score={trace.score:>5}, move={trace.move}"
                )

    out_path = ROOT / 'experiments' / 'm19' / 'depth_replay_results.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f'\nWrote results to {out_path}')


if __name__ == '__main__':
    main()
