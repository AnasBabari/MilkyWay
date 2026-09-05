"""MilkyWay M17 — Multi-task ResNet Chess Teacher Model.

Input: 18x8x8 board planes
Shared trunk: 3x3 Conv stem + Residual Tower (8-12 blocks)
Heads:
  - Policy: 1968 move logits
  - WDL: 3 logits [win, draw, loss]
  - Value: scalar in [-1, 1] (normalized centipawns via tanh)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import torch
import torch.nn as nn

from training.data.representation import MOVE_VOCABULARY_SIZE, NUM_PLANES


@dataclass
class TeacherConfig:
    in_channels: int = NUM_PLANES  # 18
    channels: int = 128
    num_blocks: int = 8
    policy_channels: int = 32
    head_hidden_dim: int = 128
    num_moves: int = MOVE_VOCABULARY_SIZE  # 1968
    name: str = "teacher_b_128x8"


TEACHER_CONFIGS: dict[str, TeacherConfig] = {
    "teacher_a": TeacherConfig(channels=96, num_blocks=8, name="teacher_a_96x8"),
    "teacher_b": TeacherConfig(channels=128, num_blocks=8, name="teacher_b_128x8"),
    "teacher_c": TeacherConfig(channels=128, num_blocks=10, name="teacher_c_128x10"),
    "teacher_d": TeacherConfig(channels=128, num_blocks=12, name="teacher_d_128x12"),
}


class ResidualBlock(nn.Module):
    """Standard 2-layer Conv residual block with BatchNorm and ReLU."""

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = self.relu(out + residual)
        return cast(torch.Tensor, out)


class ChessTeacher(nn.Module):
    """Multi-task ResNet Chess Teacher."""

    def __init__(self, config: TeacherConfig | None = None) -> None:
        super().__init__()
        if config is None:
            config = TEACHER_CONFIGS["teacher_b"]
        self.config = config

        # Stem
        self.stem = nn.Sequential(
            nn.Conv2d(config.in_channels, config.channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(config.channels),
            nn.ReLU(inplace=True),
        )

        # Residual Tower
        self.tower = nn.Sequential(
            *[ResidualBlock(config.channels) for _ in range(config.num_blocks)]
        )

        # Policy Head
        self.policy_head = nn.Sequential(
            nn.Conv2d(config.channels, config.policy_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(config.policy_channels),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(config.policy_channels * 64, config.num_moves),
        )

        # WDL Head (3 classes: win, draw, loss)
        self.wdl_head = nn.Sequential(
            nn.Conv2d(config.channels, 8, kernel_size=1, bias=False),
            nn.BatchNorm2d(8),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(8 * 64, config.head_hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(config.head_hidden_dim, 3),
        )

        # Value Head (scalar normalized centipawn)
        self.value_head = nn.Sequential(
            nn.Conv2d(config.channels, 8, kernel_size=1, bias=False),
            nn.BatchNorm2d(8),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(8 * 64, config.head_hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(config.head_hidden_dim, 1),
            nn.Tanh(),
        )

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass.

        Returns:
            policy_logits: shape (B, 1968)
            wdl_logits: shape (B, 3)
            value: shape (B, 1)
        """
        feats = self.stem(x)
        feats = self.tower(feats)

        policy_logits = self.policy_head(feats)
        wdl_logits = self.wdl_head(feats)
        value = self.value_head(feats)

        return policy_logits, wdl_logits, value

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def create_teacher(name: str = "teacher_b") -> ChessTeacher:
    """Instantiate teacher by preset name."""
    cfg = TEACHER_CONFIGS.get(name)
    if cfg is None:
        avail = list(TEACHER_CONFIGS.keys())
        raise ValueError(f"Unknown teacher config '{name}'. Available: {avail}")
    return ChessTeacher(cfg)
