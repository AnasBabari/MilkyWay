# ruff: noqa: E402
"""MilkyWay M17 — Validation Metrics and Failure Position Benchmarks.

Tracks:
  - Policy: Top-1, Top-3, Top-5 accuracy, Mean Reciprocal Rank (MRR)
  - WDL: Classification accuracy
  - Value: MAE, Sign accuracy
  - Failure position benchmark suite (including LARPMAXX Round 20 critical position)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import numpy as np
import torch
import torch.nn as nn

from training.data.representation import fen_to_tensor, move_to_index


@dataclass
class ValidationMetrics:
    loss: float = 0.0
    policy_top1: float = 0.0
    policy_top3: float = 0.0
    policy_top5: float = 0.0
    policy_mrr: float = 0.0
    wdl_acc: float = 0.0
    value_mae: float = 0.0
    value_sign_acc: float = 0.0
    samples: int = 0


def compute_batch_metrics(
    policy_logits: torch.Tensor,
    wdl_logits: torch.Tensor,
    value_pred: torch.Tensor,
    batch: dict[str, torch.Tensor],
) -> dict[str, float]:
    """Compute accuracy and error metrics on a single evaluation batch."""
    metrics: dict[str, float] = {}
    device = policy_logits.device

    # 1. Policy metrics
    policy_idx = batch["policy_idx"].to(device)
    policy_mask = batch["policy_mask"].to(device)
    valid_p = policy_mask > 0.5
    num_p = int(valid_p.sum().item())

    if num_p > 0:
        p_logits_sub = policy_logits[valid_p]
        p_targets_sub = policy_idx[valid_p]

        # Sort descending
        sorted_indices = torch.argsort(p_logits_sub, dim=-1, descending=True)
        # Ranks (1-indexed)
        matches = (sorted_indices == p_targets_sub.unsqueeze(-1))
        # Top-1, Top-3, Top-5
        top1 = matches[:, :1].any(dim=-1).float().mean().item()
        top3 = matches[:, :3].any(dim=-1).float().mean().item()
        top5 = matches[:, :5].any(dim=-1).float().mean().item()

        # MRR
        ranks = matches.nonzero()[:, 1] + 1
        mrr = (1.0 / ranks.float()).mean().item()

        metrics["policy_top1"] = top1
        metrics["policy_top3"] = top3
        metrics["policy_top5"] = top5
        metrics["policy_mrr"] = mrr
        metrics["policy_count"] = num_p

    # 2. WDL accuracy
    wdl_targets = batch["wdl"].to(device)
    wdl_mask = batch["wdl_mask"].to(device)
    valid_w = wdl_mask > 0.5
    num_w = int(valid_w.sum().item())
    if num_w > 0:
        pred_classes = torch.argmax(wdl_logits[valid_w], dim=-1)
        target_classes = torch.argmax(wdl_targets[valid_w], dim=-1)
        metrics["wdl_acc"] = (pred_classes == target_classes).float().mean().item()
        metrics["wdl_count"] = num_w

    # 3. Value MAE and Sign accuracy
    val_targets = batch["value"].to(device)
    val_mask = batch["value_mask"].to(device)
    valid_v = val_mask > 0.5
    num_v = int(valid_v.sum().item())
    if num_v > 0:
        pred_v = value_pred[valid_v].squeeze(-1)
        tgt_v = val_targets[valid_v]
        mae = torch.abs(pred_v - tgt_v).mean().item()
        # Sign accuracy (where target is non-zero)
        non_zero = torch.abs(tgt_v) > 0.05
        if non_zero.any():
            matches = torch.sign(pred_v[non_zero]) == torch.sign(tgt_v[non_zero])
            sign_correct = float(matches.float().mean().item())
        else:
            sign_correct = 1.0
        metrics["value_mae"] = mae
        metrics["value_sign_acc"] = sign_correct
        metrics["value_count"] = float(num_v)

    return metrics


# Known failure benchmark positions
FAILURE_BENCHMARK_POSITIONS: list[dict[str, Any]] = [
    {
        "name": "LARPMAXX_R20_CRITICAL",
        "fen": "1rBq1r2/1p3p1k/2n3pb/p1p4p/P3Pp1P/3P2P1/1PPQ1P2/R2R2K1 w - - 0 19",
        "blunder_move": "g3g4",
        "good_moves": ["c8h3", "c8f5", "c8e6", "c8d7", "c8b7", "c8a6"],
        "description": "MW-0.2 played g4 and hung bishop c8. Sensible retreats keep the piece.",
    },
]


def evaluate_failure_positions(
    model: nn.Module,
    device: str = "cpu",
) -> list[dict[str, Any]]:
    """Evaluate model ranking of moves in critical failure benchmark positions."""
    model.eval()
    dev = torch.device(device)
    results: list[dict[str, Any]] = []

    with torch.no_grad():
        for item in FAILURE_BENCHMARK_POSITIONS:
            fen = item["fen"]
            board = chess.Board(fen)
            legal_moves = list(board.legal_moves)
            tensor = torch.from_numpy(fen_to_tensor(fen).astype(np.float32)).unsqueeze(0).to(dev)

            # Model prediction (handle teacher tuple or student single tensor)
            out = model(tensor)
            policy_logits = out[0] if isinstance(out, tuple) else out
            logits = policy_logits[0].cpu()

            # Rank legal moves
            legal_scored: list[tuple[str, float]] = []
            for m in legal_moves:
                try:
                    idx = move_to_index(m)
                    score = float(logits[idx].item())
                    legal_scored.append((m.uci(), score))
                except (ValueError, IndexError):
                    pass

            legal_scored.sort(key=lambda x: x[1], reverse=True)
            ranked_ucis = [m for m, _ in legal_scored]

            blunder = item["blunder_move"]
            blunder_rank = ranked_ucis.index(blunder) + 1 if blunder in ranked_ucis else -1

            best_good_rank = 999
            best_good_move = ""
            for gm in item["good_moves"]:
                if gm in ranked_ucis:
                    r = ranked_ucis.index(gm) + 1
                    if r < best_good_rank:
                        best_good_rank = r
                        best_good_move = gm

            pref = best_good_rank < blunder_rank if blunder_rank != -1 else True
            res = {
                "name": item["name"],
                "blunder_move": blunder,
                "blunder_rank": blunder_rank,
                "total_legal_moves": len(legal_moves),
                "best_good_move": best_good_move,
                "best_good_rank": best_good_rank,
                "top_5_moves": ranked_ucis[:5],
                "good_preferred_over_blunder": pref,
            }
            results.append(res)

    return results
