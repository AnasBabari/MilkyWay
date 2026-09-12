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
# Floor for protocol overhead (runner IPC, referee accounting). The hard
# deadline may approach this but must never exceed the remaining clock.
PROTOCOL_FLOOR_MS: float = 20.0

# Time-management knobs, env-overridable so A/B runs need no code change.
# TM_DIVISOR spreads the usable clock over an assumed number of remaining
# moves; RESERVE_FRAC keeps a floor of the clock unspent.
def _env_float(name: str, default: float) -> float:
    import os

    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


# Defaults restored to the validated TM-B settings: an A/B over 100 paired
# games showed the more aggressive divisor was a wash (63.0% vs 62.0%), and it
# lost the held-out confirmation set, so the change bought nothing.
TM_DIVISOR: float = _env_float("MILKYWAY_TM_DIVISOR", 40.0)
TM_RESERVE_FRAC: float = _env_float("MILKYWAY_TM_RESERVE_FRAC", 0.15)
TM_RESERVE_CAP_MS: float = _env_float("MILKYWAY_TM_RESERVE_CAP_MS", 15000.0)
TM_INC_FRAC: float = _env_float("MILKYWAY_TM_INC_FRAC", 0.7)
TM_SOFT_CAP_MS: float = _env_float("MILKYWAY_TM_SOFT_CAP_MS", 6000.0)


def allocate_time(
    time_left_ms: int,
    legal_move_count: int,
    increment_ms: int = 500,
) -> TimeBudget:
    """Compute per-move soft/hard budgets in milliseconds.

    Invariant: hard_ms never exceeds the remaining clock. The safety margin
    scales down with the clock instead of being an absolute floor, because an
    absolute floor is itself a flag risk when the clock is nearly gone.
    """
    time_left = max(1.0, float(time_left_ms))
    moves = max(1, legal_move_count)

    # Emergency: critically low clock — move almost immediately.
    if time_left < 1200.0:
        soft = min(60.0, time_left * 0.06)
        hard = min(180.0, time_left * 0.20)
        emergency = True
    elif time_left < 6000.0:
        soft = time_left * 0.07
        hard = time_left * 0.25
        emergency = True
    else:
        # TM-B: Conservative 40-move divisor with up to 15.0s emergency reserve floor
        # (scaled for short arena time controls).
        reserve_floor = min(TM_RESERVE_CAP_MS, time_left * TM_RESERVE_FRAC)
        usable = max(0.0, time_left - reserve_floor)
        soft = usable / TM_DIVISOR + float(increment_ms) * TM_INC_FRAC
        hard = soft * 3.0

        # Cap opening moves so early play never risks the whole game.
        if time_left > 90000.0:
            soft = min(soft, TM_SOFT_CAP_MS)
            hard = min(hard, 12000.0)
        else:
            soft = min(soft, 5000.0, time_left * 0.15)
            hard = min(hard, 12000.0, time_left * 0.30)
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

    # Never consume the whole clock: leave a margin that scales with it.
    margin = min(SAFETY_MARGIN_MS, time_left * 0.5)
    hard = min(hard, max(PROTOCOL_FLOOR_MS, time_left - margin))
    soft = min(soft, hard)
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
