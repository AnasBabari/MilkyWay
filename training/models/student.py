"""MilkyWay M17 — Distilled Chess Policy Student Model.

Targeted for single-core CPU competition runtime:
  - Shape: 18x8x8 -> 64 channels -> 4 ResBlocks -> Policy Head
  - Vocabulary: 1968 legal moves
  - Parameter budget: ~1.3M parameters (~5 MB ONNX)
  - Single inference budget: < 5 ms on CPU
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import torch
import torch.nn as nn

from training.data.representation import MOVE_VOCABULARY_SIZE, NUM_PLANES
from training.models.teacher import ResidualBlock


@dataclass
class StudentConfig:
    in_channels: int = NUM_PLANES  # 18
    channels: int = 64
    num_blocks: int = 4
    policy_channels: int = 8
    num_moves: int = MOVE_VOCABULARY_SIZE  # 1968
    name: str = "milkyway_policy_student_64x4"


class ChessPolicyStudent(nn.Module):
    """Compact Root Policy Student for competition runtime."""

    def __init__(self, config: StudentConfig | None = None) -> None:
        super().__init__()
        if config is None:
            config = StudentConfig()
        self.config = config

        self.stem = nn.Sequential(
            nn.Conv2d(config.in_channels, config.channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(config.channels),
            nn.ReLU(inplace=True),
        )

        self.tower = nn.Sequential(
            *[ResidualBlock(config.channels) for _ in range(config.num_blocks)]
        )

        self.policy_head = nn.Sequential(
            nn.Conv2d(config.channels, config.policy_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(config.policy_channels),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(config.policy_channels * 64, config.num_moves),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Returns:
            policy_logits: shape (B, 1968)
        """
        feats = self.stem(x)
        feats = self.tower(feats)
        return cast(torch.Tensor, self.policy_head(feats))

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
