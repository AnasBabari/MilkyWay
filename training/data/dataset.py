"""MilkyWay M17 — Dataset schema, sharding, and GPU DataLoader.

Schema: m17_dataset_v1
Sharding:
  Compressed NPZ shards containing pre-encoded uint8 board tensors and targets.
  Zero FEN or PGN parsing in GPU hot loops.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from training.data.representation import (
    BOARD_SHAPE,
    fen_to_tensor,
    move_to_index,
)

SCHEMA_VERSION: str = "m17_dataset_v1"


@dataclass
class PositionRecord:
    """Canonical position record conforming to M17 dataset schema."""

    position_id: str
    fen: str
    source: str
    source_game_id: str
    source_ply: int
    side_to_move: int  # 1=White, 0=Black
    played_move: str  # UCI string
    game_result: float  # 1.0=White win, 0.5=Draw, 0.0=Black win
    stockfish_cp: float | None = None  # Centipawns from side-to-move perspective
    stockfish_wdl: list[float] | None = None  # [P(win), P(draw), P(loss)]
    stockfish_top_k: list[str] | None = None  # UCI strings
    stockfish_scores: list[float] | None = None  # Scores for top-k
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PositionRecord:
        return cls(**d)


def split_game_id(game_id: str, train_ratio: float = 0.85, val_ratio: float = 0.10) -> str:
    """Deterministically assign game to 'train', 'val', or 'test' by hashing game_id."""
    h = int(hashlib.sha256(game_id.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    if h < train_ratio:
        return "train"
    elif h < train_ratio + val_ratio:
        return "val"
    return "test"


def write_shard_npz(
    records: list[PositionRecord],
    shard_path: Path,
) -> int:
    """Encode position records into a compressed NPZ shard."""
    count = len(records)
    if count == 0:
        return 0

    boards = np.zeros((count, *BOARD_SHAPE), dtype=np.uint8)
    policy_indices = np.zeros(count, dtype=np.int64)
    policy_masks = np.zeros(count, dtype=np.float32)

    wdl_targets = np.zeros((count, 3), dtype=np.float32)
    wdl_masks = np.zeros(count, dtype=np.float32)

    value_targets = np.zeros(count, dtype=np.float32)
    value_masks = np.zeros(count, dtype=np.float32)

    # Top-K soft policy targets (up to 4 moves)
    max_k = 4
    soft_indices = np.zeros((count, max_k), dtype=np.int64)
    soft_probs = np.zeros((count, max_k), dtype=np.float32)
    soft_masks = np.zeros(count, dtype=np.float32)

    for i, rec in enumerate(records):
        boards[i] = fen_to_tensor(rec.fen)

        # Policy target
        if rec.played_move:
            try:
                idx = move_to_index(rec.played_move)
                policy_indices[i] = idx
                policy_masks[i] = 1.0
            except (ValueError, IndexError):
                pass

        # WDL target (from side-to-move perspective)
        # Game result is from White perspective: 1.0=White win, 0.5=Draw, 0.0=Black win
        if rec.game_result is not None:
            if rec.side_to_move == 1:  # White
                if rec.game_result == 1.0:
                    wdl_targets[i] = [1.0, 0.0, 0.0]  # Win
                elif rec.game_result == 0.0:
                    wdl_targets[i] = [0.0, 0.0, 1.0]  # Loss
                else:
                    wdl_targets[i] = [0.0, 1.0, 0.0]  # Draw
            else:  # Black
                if rec.game_result == 0.0:
                    wdl_targets[i] = [1.0, 0.0, 0.0]  # Win
                elif rec.game_result == 1.0:
                    wdl_targets[i] = [0.0, 0.0, 1.0]  # Loss
                else:
                    wdl_targets[i] = [0.0, 1.0, 0.0]  # Draw
            wdl_masks[i] = 1.0

        # Stockfish WDL override if present
        if rec.stockfish_wdl is not None and len(rec.stockfish_wdl) == 3:
            wdl_targets[i] = np.array(rec.stockfish_wdl, dtype=np.float32)
            wdl_masks[i] = 1.0

        # Value target: normalized centipawn = tanh(cp / 600)
        if rec.stockfish_cp is not None:
            clamped_cp = np.clip(rec.stockfish_cp, -1500.0, 1500.0)
            value_targets[i] = float(np.tanh(clamped_cp / 600.0))
            value_masks[i] = 1.0
        elif rec.game_result is not None:
            # Fallback value from game result: +1.0 for win, 0.0 for draw, -1.0 for loss
            v = (rec.game_result - 0.5) * 2.0
            if rec.side_to_move == 0:
                v = -v
            value_targets[i] = float(v)
            value_masks[i] = 1.0

        # Soft policy from Stockfish top-K
        if (
            rec.stockfish_top_k is not None
            and rec.stockfish_scores is not None
            and len(rec.stockfish_top_k) > 0
        ):
            k = min(len(rec.stockfish_top_k), max_k)
            scores = np.array(rec.stockfish_scores[:k], dtype=np.float32)
            # Temperature scaling for soft target: temperature = 100 cp
            temp = 100.0
            exp_scores = np.exp((scores - np.max(scores)) / temp)
            probs = exp_scores / np.sum(exp_scores)
            valid_k = 0
            for ki, move_str in enumerate(rec.stockfish_top_k[:k]):
                try:
                    m_idx = move_to_index(move_str)
                    soft_indices[i, valid_k] = m_idx
                    soft_probs[i, valid_k] = probs[ki]
                    valid_k += 1
                except (ValueError, IndexError):
                    pass
            if valid_k > 0:
                # Renormalize
                soft_probs[i, :valid_k] /= np.sum(soft_probs[i, :valid_k])
                soft_masks[i] = 1.0

    shard_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        shard_path,
        boards=boards,
        policy_indices=policy_indices,
        policy_masks=policy_masks,
        wdl_targets=wdl_targets,
        wdl_masks=wdl_masks,
        value_targets=value_targets,
        value_masks=value_masks,
        soft_indices=soft_indices,
        soft_probs=soft_probs,
        soft_masks=soft_masks,
    )
    return count


class ShardedChessDataset(Dataset[dict[str, torch.Tensor]]):
    """Memory-efficient Dataset loading pre-sharded NPZ files into RAM."""

    def __init__(self, shard_paths: list[Path], preload: bool = True) -> None:
        self.shard_paths = [p for p in shard_paths if p.exists()]
        if not self.shard_paths:
            raise ValueError("No valid shard paths provided")

        self.preload = preload
        if preload:
            all_boards = []
            all_policy_indices = []
            all_policy_masks = []
            all_wdl = []
            all_wdl_masks = []
            all_val = []
            all_val_masks = []
            all_soft_idx = []
            all_soft_prob = []
            all_soft_mask = []

            for p in self.shard_paths:
                npz = np.load(p)
                all_boards.append(npz["boards"])
                all_policy_indices.append(npz["policy_indices"])
                all_policy_masks.append(npz["policy_masks"])
                all_wdl.append(npz["wdl_targets"])
                all_wdl_masks.append(npz["wdl_masks"])
                all_val.append(npz["value_targets"])
                all_val_masks.append(npz["value_masks"])
                all_soft_idx.append(npz["soft_indices"])
                all_soft_prob.append(npz["soft_probs"])
                all_soft_mask.append(npz["soft_masks"])

            self.boards = np.concatenate(all_boards, axis=0)
            self.policy_indices = np.concatenate(all_policy_indices, axis=0)
            self.policy_masks = np.concatenate(all_policy_masks, axis=0)
            self.wdl_targets = np.concatenate(all_wdl, axis=0)
            self.wdl_masks = np.concatenate(all_wdl_masks, axis=0)
            self.value_targets = np.concatenate(all_val, axis=0)
            self.value_masks = np.concatenate(all_val_masks, axis=0)
            self.soft_indices = np.concatenate(all_soft_idx, axis=0)
            self.soft_probs = np.concatenate(all_soft_prob, axis=0)
            self.soft_masks = np.concatenate(all_soft_mask, axis=0)
            self.total_count = int(self.boards.shape[0])
        else:
            self.shard_lengths: list[int] = []
            self.cumulative_lengths: list[int] = []
            total = 0
            for p in self.shard_paths:
                data = np.load(p, mmap_mode="r")
                n = int(data["boards"].shape[0])
                self.shard_lengths.append(n)
                total += n
                self.cumulative_lengths.append(total)
            self._cached_shard_idx: int = -1
            self._cached_data: dict[str, np.ndarray] | None = None
            self.total_count = total

    def __len__(self) -> int:
        return int(self.total_count)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        if self.preload:
            board = torch.from_numpy(self.boards[idx].astype(np.float32))
            policy_idx = torch.tensor(self.policy_indices[idx], dtype=torch.long)
            policy_mask = torch.tensor(self.policy_masks[idx], dtype=torch.float32)
            wdl = torch.from_numpy(self.wdl_targets[idx].astype(np.float32))
            wdl_mask = torch.tensor(self.wdl_masks[idx], dtype=torch.float32)
            val = torch.tensor(self.value_targets[idx], dtype=torch.float32)
            val_mask = torch.tensor(self.value_masks[idx], dtype=torch.float32)
            soft_idx = torch.from_numpy(self.soft_indices[idx].astype(np.int64))
            soft_pr = torch.from_numpy(self.soft_probs[idx].astype(np.float32))
            soft_m = torch.tensor(self.soft_masks[idx], dtype=torch.float32)
            return {
                "board": board,
                "policy_idx": policy_idx,
                "policy_mask": policy_mask,
                "wdl": wdl,
                "wdl_mask": wdl_mask,
                "value": val,
                "value_mask": val_mask,
                "soft_idx": soft_idx,
                "soft_prob": soft_pr,
                "soft_mask": soft_m,
            }

        shard_idx = int(np.searchsorted(self.cumulative_lengths, idx, side="right"))
        offset = idx if shard_idx == 0 else idx - self.cumulative_lengths[shard_idx - 1]
        if self._cached_shard_idx != shard_idx or self._cached_data is None:
            npz = np.load(self.shard_paths[shard_idx])
            self._cached_data = {k: npz[k] for k in npz.files}
            self._cached_shard_idx = shard_idx
        shard = self._cached_data

        board = torch.from_numpy(shard["boards"][offset].astype(np.float32))
        policy_idx = torch.tensor(shard["policy_indices"][offset], dtype=torch.long)
        policy_mask = torch.tensor(shard["policy_masks"][offset], dtype=torch.float32)
        wdl = torch.from_numpy(shard["wdl_targets"][offset].astype(np.float32))
        wdl_mask = torch.tensor(shard["wdl_masks"][offset], dtype=torch.float32)
        val = torch.tensor(shard["value_targets"][offset], dtype=torch.float32)
        val_mask = torch.tensor(shard["value_masks"][offset], dtype=torch.float32)
        soft_idx = torch.from_numpy(shard["soft_indices"][offset].astype(np.int64))
        soft_pr = torch.from_numpy(shard["soft_probs"][offset].astype(np.float32))
        soft_m = torch.tensor(shard["soft_masks"][offset], dtype=torch.float32)

        return {
            "board": board,
            "policy_idx": policy_idx,
            "policy_mask": policy_mask,
            "wdl": wdl,
            "wdl_mask": wdl_mask,
            "value": val,
            "value_mask": val_mask,
            "soft_idx": soft_idx,
            "soft_prob": soft_pr,
            "soft_mask": soft_m,
        }


def create_dataloader(
    dataset: ShardedChessDataset,
    batch_size: int,
    shuffle: bool = True,
    num_workers: int = 4,
    pin_memory: bool = True,
) -> DataLoader[dict[str, torch.Tensor]]:
    """Create configured DataLoader with worker prefetching."""
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory and torch.cuda.is_available(),
        persistent_workers=(num_workers > 0),
        prefetch_factor=2 if num_workers > 0 else None,
    )
