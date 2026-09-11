"""MilkyWay flagship — joint policy + value network.

Same 18x8x8 input and trunk shape as the policy student (stem 64ch + 4
ResBlocks) so trunk/policy weights warm-start from best_student.pt. Adds a
small 3-way WDL value head (win/draw/loss from side-to-move perspective)
trained with cross-entropy, which keeps gradients alive in decisive
positions where tanh regression saturates. Total ~1.45M parameters; one
forward pass serves root move ordering AND root position evaluation.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from training.data.representation import MOVE_VOCABULARY_SIZE, NUM_PLANES
from training.models.student import StudentConfig
from training.models.teacher import ResidualBlock


class ChessFlagshipNet(nn.Module):
    """Joint policy + value network for competition runtime."""

    def __init__(self, channels: int = 64, num_blocks: int = 4) -> None:
        super().__init__()
        self.config = StudentConfig(
            in_channels=NUM_PLANES,
            channels=channels,
            num_blocks=num_blocks,
            name="milkyway_flagship_64x4_pv",
        )

        self.stem = nn.Sequential(
            nn.Conv2d(NUM_PLANES, channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True),
        )
        self.tower = nn.Sequential(*[ResidualBlock(channels) for _ in range(num_blocks)])
        self.policy_head = nn.Sequential(
            nn.Conv2d(channels, 8, kernel_size=1, bias=False),
            nn.BatchNorm2d(8),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(8 * 64, MOVE_VOCABULARY_SIZE),
        )
        self.value_head = nn.Sequential(
            nn.Conv2d(channels, 16, kernel_size=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(16 * 64, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, 3),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Returns (policy_logits (B, 1968), value_wdl_logits (B, 3))."""
        feats = self.tower(self.stem(x))
        return self.policy_head(feats), self.value_head(feats)

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def load_policy_warm_start(
    model: ChessFlagshipNet,
    checkpoint_path: str,
    verbose: bool = True,
    full: bool = False,
) -> set[str]:
    """Load weights from a previous checkpoint.

    By default loads trunk + policy only (value head stays fresh, for
    policy-student checkpoints). With full=True loads every matching tensor
    including the value head (for continuing flagship training).
    Returns the set of parameter names that were loaded.
    """
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    state = ckpt.get("model_state_dict", ckpt)
    own = model.state_dict()
    loaded: set[str] = set()
    for name, tensor in state.items():
        if name in own and own[name].shape == tensor.shape:
            if not full and name.startswith("value_head"):
                continue
            own[name].copy_(tensor)
            loaded.add(name)
    if verbose:
        print(f"warm start: {len(loaded)} tensors loaded (full={full})")
    return loaded
