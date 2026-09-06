"""Deterministic clock management simulation for 600-ply games under 120s + 0.5s TC."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import time_manager  # noqa: E402


def run_simulation(
    name: str, consumption_ratio: float = 1.0, typical_moves: int = 25
) -> list[dict[str, float]]:
    clock_ms = 120_000.0  # 120s base
    increment_ms = 500.0   # 0.5s increment
    checkpoints = [10, 25, 50, 100, 150, 200, 250, 295, 300]
    records: list[dict[str, float]] = []

    for move in range(1, 301):
        budget = time_manager.allocate_time(int(clock_ms), typical_moves, int(increment_ms))
        consumed = min(budget.hard_ms, budget.soft_ms * consumption_ratio)
        clock_ms -= consumed
        if clock_ms < 0:
            raise RuntimeError(f"Flag fall at move {move}: clock={clock_ms:.1f}ms")
        clock_ms += increment_ms

        if move in checkpoints:
            records.append({
                "move": move,
                "clock_s": clock_ms / 1000.0,
                "soft_ms": budget.soft_ms,
                "hard_ms": budget.hard_ms,
                "emergency": 1.0 if budget.emergency else 0.0,
            })
    return records


def main() -> None:
    scenarios = [
        ("Nominal (1.0x soft)", 1.0),
        ("Moderate (0.8x soft)", 0.8),
        ("Overrun (1.2x soft)", 1.2),
        ("Heavy Stress (1.5x soft)", 1.5),
    ]

    print("=" * 80)
    print("LONG-GAME CLOCK TRAJECTORY SIMULATION (120s + 0.5s, 300 moves per side / 600 plies)")
    print("=" * 80)

    for name, ratio in scenarios:
        print(f"\n--- Scenario: {name} ---")
        records = run_simulation(name, ratio)
        header = (
            f"{'Move':>5} | {'Clock (s)':>9} | {'Soft (ms)':>9} | "
            f"{'Hard (ms)':>9} | {'Mode':>9}"
        )
        print(header)
        print("-" * len(header))
        for r in records:
            mode = "EMERGENCY" if r["emergency"] else "NORMAL"
            row = (
                f"{int(r['move']):6d} | {r['clock_s']:10.2f} | {r['soft_ms']:10.1f} | "
                f"{r['hard_ms']:10.1f} | {mode:>10}"
            )
            print(row)


if __name__ == "__main__":
    main()
