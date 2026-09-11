"""Shared engine types for MilkyWay."""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass, field

import chess


@dataclass
class TTEntry:
    """One transposition-table entry."""

    key: Hashable
    depth: int
    score: int
    bound: int
    best_move: chess.Move | None
    generation: int


@dataclass
class SearchStats:
    """Counters for development telemetry (kept minimal in production)."""

    nodes: int = 0
    qnodes: int = 0
    seldepth: int = 0
    tt_probes: int = 0
    tt_hits: int = 0
    tt_cutoffs: int = 0
    beta_cutoffs: int = 0
    null_cutoffs: int = 0
    lmr_researches: int = 0
    elapsed_ms: float = 0.0
    depth_reached: int = 0
    score: int = 0
    pv: list[str] = field(default_factory=list)


class SearchTimeout(Exception):
    """Raised when the hard deadline expires inside search."""
