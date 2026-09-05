"""Comprehensive evaluation metrics for tuned MilkyWay coefficients on held-out test data.

Computes:
- MAE, Median AE, RMSE
- Sign accuracy (positions with |y| >= 25 cp)
- Pearson correlation
- Pairwise ordering accuracy
- Breakdown by phase (opening, middlegame, endgame)
- Breakdown by score magnitude (equal, moderate, large)
- Side-by-side comparison against MW-0.2 baseline
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constants import (  # noqa: E402
    MW_0_2_EVAL,
    EvalParameters,
)


def compute_metrics(
    X: np.ndarray,
    y: np.ndarray,
    fixed: np.ndarray,
    beta: np.ndarray,
    jsonl_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    preds = X @ beta + fixed
    errors = y - preds
    abs_errors = np.abs(errors)

    mae = float(np.mean(abs_errors))
    med_ae = float(np.median(abs_errors))
    rmse = float(np.sqrt(np.mean(errors**2)))

    # Sign accuracy (positions with |y| >= 25 cp)
    significant = np.abs(y) >= 25.0
    if np.any(significant):
        correct_sign = np.sign(preds[significant]) == np.sign(y[significant])
        sign_acc = float(np.mean(correct_sign))
    else:
        sign_acc = 1.0

    # Pearson correlation
    r = (
        float(np.corrcoef(preds, y)[0, 1])
        if np.std(preds) > 1e-4 and np.std(y) > 1e-4
        else 0.0
    )

    # Pairwise ordering accuracy: sample 2000 random pairs
    rng = random.Random(42)
    n = len(y)
    pairs_tested = 0
    pairs_correct = 0
    for _ in range(min(5000, n * 5)):
        i, j = rng.randrange(n), rng.randrange(n)
        if i == j:
            continue
        dy = y[i] - y[j]
        if abs(dy) >= 25.0:
            pairs_tested += 1
            d_pred = preds[i] - preds[j]
            if (dy > 0 and d_pred > 0) or (dy < 0 and d_pred < 0):
                pairs_correct += 1

    pairwise_acc = (pairs_correct / pairs_tested) if pairs_tested > 0 else 1.0

    metrics: dict[str, Any] = {
        "count": int(n),
        "mae": round(mae, 2),
        "med_ae": round(med_ae, 2),
        "rmse": round(rmse, 2),
        "sign_acc": round(sign_acc * 100.0, 1),
        "pearson_r": round(r, 4),
        "pairwise_acc": round(pairwise_acc * 100.0, 1),
    }

    # Stratified metrics by phase and score bucket if records available
    if jsonl_records and len(jsonl_records) == n:
        phases = np.array([r.get("game_phase", 12) for r in jsonl_records])
        abs_y = np.abs(y)

        # Phase subsets
        mask_open = phases >= 20
        mask_mid = (phases >= 8) & (phases < 20)
        mask_end = phases < 8

        # Advantage subsets
        mask_eq = abs_y < 50.0
        mask_mod = (abs_y >= 50.0) & (abs_y < 300.0)
        mask_large = abs_y >= 300.0

        def sub_mae(m: np.ndarray) -> float:
            return round(float(np.mean(abs_errors[m])), 2) if np.any(m) else 0.0

        metrics["phase_mae"] = {
            "opening": sub_mae(mask_open),
            "middlegame": sub_mae(mask_mid),
            "endgame": sub_mae(mask_end),
        }
        metrics["bucket_mae"] = {
            "equal_<50cp": sub_mae(mask_eq),
            "moderate_50_300cp": sub_mae(mask_mod),
            "large_>=300cp": sub_mae(mask_large),
        }

    return metrics


def evaluate_candidate(
    npz_path: Path,
    candidate_json_path: Path | None = None,
    test_jsonl_path: Path | None = None,
) -> dict[str, Any]:
    data = np.load(npz_path)
    X_test = data["X_test"]
    y_test = data["y_test"]
    fixed_test = data["fixed_test"]

    records: list[dict[str, Any]] = []
    if test_jsonl_path and test_jsonl_path.exists():
        with test_jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

    # Baseline MW-0.2 metrics
    beta_0 = np.array(MW_0_2_EVAL.get_tunable_vector(), dtype=np.float32)
    baseline_metrics = compute_metrics(X_test, y_test, fixed_test, beta_0, records)

    # Candidate metrics
    if candidate_json_path and candidate_json_path.exists():
        cand_data = json.loads(candidate_json_path.read_text(encoding="utf-8"))
        cand_params = EvalParameters.from_dict(cand_data["parameters"])
        cand_beta = np.array(cand_params.get_tunable_vector(), dtype=np.float32)
        cand_metrics = compute_metrics(X_test, y_test, fixed_test, cand_beta, records)
    else:
        cand_metrics = baseline_metrics

    return {
        "baseline_mw_0_2": baseline_metrics,
        "candidate": cand_metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate fit metrics on test set.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("training/datasets/processed/dataset.npz"),
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=Path("training/output/eval_coefficients.json"),
    )
    parser.add_argument(
        "--test-jsonl",
        type=Path,
        default=Path("training/datasets/processed/test.jsonl"),
    )
    args = parser.parse_args()

    results = evaluate_candidate(
        npz_path=args.dataset,
        candidate_json_path=args.candidate,
        test_jsonl_path=args.test_jsonl,
    )

    base = results["baseline_mw_0_2"]
    cand = results["candidate"]

    print("=== Held-out Test Set Evaluation ===")
    print(f"Test positions: {base['count']}")
    print(f"{'Metric':<22} {'MW-0.2 Baseline':>15} {'Tuned Candidate':>15} {'Delta':>15}")
    print("-" * 70)
    metrics = [
        (
            "MAE",
            f"{base['mae']:.2f} cp",
            f"{cand['mae']:.2f} cp",
            f"{cand['mae'] - base['mae']:+.2f} cp",
        ),
        (
            "Median AE",
            f"{base['med_ae']:.2f} cp",
            f"{cand['med_ae']:.2f} cp",
            f"{cand['med_ae'] - base['med_ae']:+.2f} cp",
        ),
        (
            "RMSE",
            f"{base['rmse']:.2f} cp",
            f"{cand['rmse']:.2f} cp",
            f"{cand['rmse'] - base['rmse']:+.2f} cp",
        ),
        (
            "Sign Accuracy",
            f"{base['sign_acc']:.1f}%",
            f"{cand['sign_acc']:.1f}%",
            f"{cand['sign_acc'] - base['sign_acc']:+.1f}%",
        ),
        (
            "Pearson r",
            f"{base['pearson_r']:.4f}",
            f"{cand['pearson_r']:.4f}",
            f"{cand['pearson_r'] - base['pearson_r']:+.4f}",
        ),
        (
            "Pairwise Order Acc",
            f"{base['pairwise_acc']:.1f}%",
            f"{cand['pairwise_acc']:.1f}%",
            f"{cand['pairwise_acc'] - base['pairwise_acc']:+.1f}%",
        ),
    ]
    for name, b_val, c_val, d_val in metrics:
        print(f"{name:<22} {b_val:>15} {c_val:>15} {d_val:>15}")

    if "phase_mae" in base and "phase_mae" in cand:
        print("\nPhase MAE:")
        for ph in ("opening", "middlegame", "endgame"):
            b_ph = base["phase_mae"][ph]
            c_ph = cand["phase_mae"][ph]
            delta = c_ph - b_ph
            print(f"  {ph:<12}: {b_ph:5.1f} -> {c_ph:5.1f} cp ({delta:+5.1f} cp)")

    if "bucket_mae" in base and "bucket_mae" in cand:
        print("\nAdvantage Bucket MAE:")
        for bk in ("equal_<50cp", "moderate_50_300cp", "large_>=300cp"):
            b_bk = base["bucket_mae"][bk]
            c_bk = cand["bucket_mae"][bk]
            delta = c_bk - b_bk
            print(f"  {bk:<18}: {b_bk:5.1f} -> {c_bk:5.1f} cp ({delta:+5.1f} cp)")


if __name__ == "__main__":
    main()
