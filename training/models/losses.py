"""MilkyWay M17 — Multi-task masked loss functions.

Supports:
  - Policy: Hard target cross-entropy + Soft Stockfish MultiPV KL / cross-entropy
  - WDL: 3-class distribution cross-entropy
  - Value: Huber loss on normalized centipawns
All losses cleanly support zero-masking for incomplete / mixed datasets.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812


@dataclass
class LossWeights:
    policy: float = 1.0
    wdl: float = 0.5
    value: float = 0.2


class MultiTaskChessLoss(nn.Module):
    """Masked multi-task loss for chess teacher training."""

    def __init__(self, weights: LossWeights | None = None) -> None:
        super().__init__()
        self.weights = weights if weights is not None else LossWeights()

    def forward(
        self,
        policy_logits: torch.Tensor,
        wdl_logits: torch.Tensor,
        value_pred: torch.Tensor,
        batch: dict[str, torch.Tensor],
    ) -> dict[str, torch.Tensor]:
        device = policy_logits.device

        # 1. Policy Loss
        policy_idx = batch["policy_idx"].to(device)
        policy_mask = batch["policy_mask"].to(device)
        soft_idx = batch.get("soft_idx")
        soft_prob = batch.get("soft_prob")
        soft_mask = batch.get("soft_mask")

        log_probs = F.log_softmax(policy_logits, dim=-1)

        # Hard cross entropy
        hard_ce = F.cross_entropy(policy_logits, policy_idx, reduction="none")

        # Soft cross entropy if soft targets present
        if soft_idx is not None and soft_prob is not None and soft_mask is not None:
            soft_idx = soft_idx.to(device)
            soft_prob = soft_prob.to(device)
            soft_mask = soft_mask.to(device)

            # Gather log probs at soft indices
            gathered_log_probs = torch.gather(log_probs, dim=1, index=soft_idx)
            soft_ce = -(soft_prob * gathered_log_probs).sum(dim=-1)

            # Combine: where soft_mask is 1, use soft_ce; else use hard_ce with policy_mask
            has_soft = (soft_mask > 0.5).float()
            sample_policy_loss = (
                has_soft * soft_ce + (1.0 - has_soft) * hard_ce * policy_mask
            )
            total_policy_mask = torch.clamp(has_soft + policy_mask, 0.0, 1.0)
            policy_loss = (
                (sample_policy_loss * total_policy_mask).sum()
                / (total_policy_mask.sum() + 1e-8)
            )
        else:
            policy_loss = (hard_ce * policy_mask).sum() / (policy_mask.sum() + 1e-8)

        # 2. WDL Loss (3 classes: win, draw, loss)
        wdl_targets = batch["wdl"].to(device)
        wdl_mask = batch["wdl_mask"].to(device)
        wdl_log_probs = F.log_softmax(wdl_logits, dim=-1)
        sample_wdl_loss = -(wdl_targets * wdl_log_probs).sum(dim=-1)
        wdl_loss = (sample_wdl_loss * wdl_mask).sum() / (wdl_mask.sum() + 1e-8)

        # 3. Value Loss (Huber on normalized centipawns)
        value_targets = batch["value"].to(device)
        value_mask = batch["value_mask"].to(device)
        val_squeeze = value_pred.squeeze(-1)
        sample_val_loss = F.smooth_l1_loss(val_squeeze, value_targets, reduction="none")
        value_loss = (sample_val_loss * value_mask).sum() / (value_mask.sum() + 1e-8)

        # Total combined loss
        total_loss = (
            self.weights.policy * policy_loss
            + self.weights.wdl * wdl_loss
            + self.weights.value * value_loss
        )

        return {
            "loss": total_loss,
            "policy_loss": policy_loss,
            "wdl_loss": wdl_loss,
            "value_loss": value_loss,
        }
