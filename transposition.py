"""Bounded transposition table with generation-based replacement."""

from __future__ import annotations

from collections.abc import Hashable

import chess

from constants import EXACT
from engine_types import TTEntry


class TranspositionTable:
    """Fixed-capacity dict with prefer-deep + prefer-recent replacement."""

    def __init__(self, max_entries: int = 131072) -> None:
        self._table: dict[Hashable, TTEntry] = {}
        self._max_entries = max_entries
        self._generation = 0

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def size(self) -> int:
        return len(self._table)

    def new_generation(self) -> None:
        self._generation += 1

    def clear(self) -> None:
        self._table.clear()
        self._generation = 0

    def probe(self, key: Hashable) -> TTEntry | None:
        return self._table.get(key)

    def store(
        self,
        key: Hashable,
        depth: int,
        score: int,
        bound: int,
        best_move: chess.Move | None,
    ) -> None:
        existing = self._table.get(key)
        if existing is not None:
            # Replacement: newer generation wins; same generation prefers
            # deeper searches, then exact scores.
            if existing.generation == self._generation:
                if existing.depth > depth:
                    # Keep deeper entry, but refresh best move if we have one.
                    if best_move is not None and existing.best_move is None:
                        existing.best_move = best_move
                    return
                if existing.depth == depth and existing.bound == EXACT and bound != EXACT:
                    if best_move is not None:
                        existing.best_move = best_move
                    return
        elif len(self._table) >= self._max_entries:
            self._evict_one()
        self._table[key] = TTEntry(
            key=key,
            depth=depth,
            score=score,
            bound=bound,
            best_move=best_move,
            generation=self._generation,
        )

    def _evict_one(self) -> None:
        # Evict in O(1) time using dict FIFO order. Avoids scanning up to 131k
        # items when the transposition table reaches capacity.
        try:
            oldest_key = next(iter(self._table))
            del self._table[oldest_key]
        except StopIteration:
            pass
