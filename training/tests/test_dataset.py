"""Unit tests for M17 dataset schema, splitting, and sharded loading."""

from __future__ import annotations

import tempfile
from pathlib import Path

import torch

from training.data.collector import generate_selfplay_positions, get_curated_positions
from training.data.dataset import (
    PositionRecord,
    ShardedChessDataset,
    create_dataloader,
    split_game_id,
    write_shard_npz,
)


def test_position_record_serialization() -> None:
    rec = PositionRecord(
        position_id="test_01",
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        source="unit_test",
        source_game_id="game_123",
        source_ply=2,
        side_to_move=0,
        played_move="e7e5",
        game_result=0.5,
        stockfish_cp=15.0,
        stockfish_wdl=[0.3, 0.4, 0.3],
        stockfish_top_k=["e7e5", "c7c5"],
        stockfish_scores=[15.0, 10.0],
    )
    d = rec.to_dict()
    assert d["position_id"] == "test_01"
    assert d["schema_version"] == "m17_dataset_v1"

    rec2 = PositionRecord.from_dict(d)
    assert rec2.position_id == rec.position_id
    assert rec2.stockfish_top_k == ["e7e5", "c7c5"]


def test_game_level_splitting_no_leakage() -> None:
    game_a = "lichess_tournament_game_12345"
    game_b = "lichess_tournament_game_67890"

    # Positions from same game MUST get same split
    split_a1 = split_game_id(game_a)
    split_a2 = split_game_id(game_a)
    assert split_a1 == split_a2
    assert split_a1 in ("train", "val", "test")

    split_b = split_game_id(game_b)
    assert split_b in ("train", "val", "test")


def test_curated_positions_collection() -> None:
    curated = get_curated_positions()
    # 200 test bank + 40 benchmark suite (with 3 duplicates deduplicated) + 1 larpmaxx = 238
    assert len(curated) >= 235
    larp = next((r for r in curated if r.position_id == "rated_larpmaxx_r20_critical"), None)
    assert larp is not None
    assert larp.side_to_move == 1
    assert "1rBq1r2" in larp.fen


def test_shard_creation_and_dataloader() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        shard_path = tmp_path / "shard_00000.npz"

        # Generate a few self-play positions
        records = generate_selfplay_positions(target_positions=20, depth=1, seed=99)
        assert len(records) >= 20

        written = write_shard_npz(records, shard_path)
        assert written >= 20
        assert shard_path.exists()

        # Load with ShardedChessDataset
        dataset = ShardedChessDataset([shard_path])
        assert len(dataset) == written

        sample = dataset[0]
        assert "board" in sample
        assert sample["board"].shape == (18, 8, 8)
        assert sample["board"].dtype == torch.float32
        assert sample["policy_idx"].dtype == torch.long
        assert sample["wdl"].shape == (3,)
        assert sample["value"].ndim == 0

        # DataLoader test
        loader = create_dataloader(dataset, batch_size=8, shuffle=False, num_workers=0)
        batch = next(iter(loader))
        assert batch["board"].shape == (8, 18, 8, 8)
        assert batch["policy_idx"].shape == (8,)
        assert batch["wdl"].shape == (8, 3)
