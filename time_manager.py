"""Time management with soft (stop iterating) and hard (abort now) deadlines."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class TimeBudget:
    soft_ms: float
    hard_ms: float
    emergency: bool


SAFETY_MARGIN_MS: float = 300.0
MIN_HARD_MS: float = 60.0
MIN_SOFT_MS: float = 25.0


def allocate_time(
    time_left_ms: int,
    legal_move_count: int,
    increment_ms: int = 500,
) -> TimeBudget:
    """Compute per-move soft/hard budgets in milliseconds."""
    time_left = max(1.0, float(time_left_ms))
    moves = max(1, legal_move_count)

    # Emergency: critically low clock — move almost immediately.
    if time_left < 1200.0:
        soft = max(MIN_SOFT_MS, min(60.0, time_left * 0.06))
        hard = max(MIN_HARD_MS, min(180.0, time_left * 0.20))
        return TimeBudget(soft_ms=soft, hard_ms=hard, emergency=True)
    if time_left < 6000.0:
        soft = time_left * 0.07
        hard = time_left * 0.25
        emergency = True
    else:
        # Baseline: ~1/25th of remaining + most of the increment.
        soft = time_left / 25.0 + float(increment_ms) * 0.7
        hard = soft * 3.0
        # Cap so one move never risks the whole game.
        soft = min(soft, 5000.0, time_left * 0.20)
        hard = min(hard, 12000.0, time_left * 0.35)
        emergency = False

    # Single legal move: barely think.
    if moves <= 1:
        soft = min(soft, 30.0)
        hard = min(hard, 150.0)
    elif moves <= 3:
        soft *= 0.55
        hard *= 0.7
    elif moves >= 35:
        soft *= 1.15

    soft = max(MIN_SOFT_MS, soft)
    hard = max(MIN_HARD_MS, hard)

    # Always leave a safety margin so wall-clock jitter cannot flag us.
    hard = min(hard, max(MIN_HARD_MS, time_left - SAFETY_MARGIN_MS))
    soft = min(soft, max(MIN_SOFT_MS, time_left - SAFETY_MARGIN_MS - 50.0))
    if soft > hard:
        soft = hard * 0.5
    return TimeBudget(soft_ms=soft, hard_ms=hard, emergency=emergency)


class Clock:
    """Monotonic deadlines derived from a TimeBudget."""

    def __init__(self) -> None:
        self.soft_deadline = 0.0
        self.hard_deadline = 0.0
        self.start = 0.0
        self.emergency = False

    def start_move(self, budget: TimeBudget) -> None:
        self.start = time.monotonic()
        self.soft_deadline = self.start + budget.soft_ms / 1000.0
        self.hard_deadline = self.start + budget.hard_ms / 1000.0
        self.emergency = budget.emergency

    def elapsed_ms(self) -> float:
        return (time.monotonic() - self.start) * 1000.0

    def past_soft(self) -> bool:
        return time.monotonic() >= self.soft_deadline

    def past_hard(self) -> bool:
        return time.monotonic() >= self.hard_deadline
