"""Linear and robust fitting of MilkyWay evaluation coefficients using NumPy.

Supports:
- Ridge regression regularized toward MW-0.2 baseline
- Huber-style robust regression via Iteratively Reweighted Least Squares (IRLS)
- Validation sweep over regularization strength lambda
- Coefficient sanity constraints and bounded projection
- Detailed parameter diff report and export to JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constants import (  # noqa: E402
    MW_0_2_EVAL,
    TUNABLE_PARAM_NAMES,
    EvalParameters,
)

PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "pawn_value_mg": (60.0, 150.0),
    "pawn_value_eg": (60.0, 160.0),
    "knight_value_mg": (250.0, 420.0),
    "knight_value_eg": (250.0, 420.0),
    "bishop_value_mg": (260.0, 430.0),
    "bishop_value_eg": (260.0, 430.0),
    "rook_value_mg": (400.0, 650.0),
    "rook_value_eg": (400.0, 650.0),
    "queen_value_mg": (750.0, 1200.0),
    "queen_value_eg": (750.0, 1200.0),
    "bishop_pair_mg": (0.0, 80.0),
    "bishop_pair_eg": (0.0, 100.0),
    "mobility_knight": (0.0, 8.0),
    "mobility_bishop": (0.0, 8.0),
    "mobility_rook": (0.0, 6.0),
    "mobility_queen": (0.0, 4.0),
    "doubled_pawn_mg": (-35.0, 0.0),
    "doubled_pawn_eg": (-45.0, 0.0),
    "isolated_pawn_mg": (-40.0, 0.0),
    "isolated_pawn_eg": (-50.0, 0.0),
    "backward_pawn_mg": (-30.0, 0.0),
    "backward_pawn_eg": (-35.0, 0.0),
    "connected_pawn_mg": (0.0, 30.0),
    "connected_pawn_eg": (0.0, 30.0),
    "protected_passer_mg": (0.0, 40.0),
    "protected_passer_eg": (0.0, 50.0),
    "rook_open_file_mg": (0.0, 40.0),
    "rook_open_file_eg": (0.0, 30.0),
    "rook_semi_open_mg": (0.0, 25.0),
    "rook_semi_open_eg": (0.0, 20.0),
    "rook_seventh_mg": (0.0, 50.0),
    "rook_seventh_eg": (0.0, 60.0),
    "rook_connected_mg": (0.0, 30.0),
    "rook_behind_passer_mg": (0.0, 40.0),
    "rook_behind_passer_eg": (0.0, 50.0),
    "king_shield_missing": (-40.0, 0.0),
    "king_open_file_near": (-40.0, 0.0),
    "king_attack_unit": (-25.0, 0.0),
}


def fit_ridge(
    X_train: np.ndarray,
    y_train: np.ndarray,
    fixed_train: np.ndarray,
    beta_0: np.ndarray,
    reg_lambda: float,
) -> np.ndarray:
    """Solve min ||X (beta_0 + d_beta) + fixed - y||^2 + lambda ||d_beta||^2."""
    r_base = (y_train - fixed_train) - X_train @ beta_0
    XtX = X_train.T @ X_train
    I_mat = np.eye(X_train.shape[1], dtype=np.float32)
    d_beta = np.linalg.solve(XtX + reg_lambda * I_mat, X_train.T @ r_base)
    return beta_0 + d_beta


def fit_huber(
    X_train: np.ndarray,
    y_train: np.ndarray,
    fixed_train: np.ndarray,
    beta_0: np.ndarray,
    reg_lambda: float,
    delta: float = 100.0,
    max_iter: int = 10,
) -> np.ndarray:
    """Iteratively Reweighted Least Squares (IRLS) for Huber loss."""
    beta = beta_0.copy()
    I_mat = np.eye(X_train.shape[1], dtype=np.float32)

    for _ in range(max_iter):
        preds = X_train @ beta + fixed_train
        errors = y_train - preds
        abs_e = np.abs(errors)
        weights = np.where(abs_e <= delta, 1.0, delta / np.maximum(abs_e, 1e-6))

        # Weighted least squares
        WX = X_train * weights[:, None]
        r_base = (y_train - fixed_train) - X_train @ beta_0
        XtWX = X_train.T @ WX
        d_beta = np.linalg.solve(XtWX + reg_lambda * I_mat, X_train.T @ (weights * r_base))
        beta = beta_0 + d_beta

    return beta


def enforce_sanity_bounds(beta: np.ndarray) -> np.ndarray:
    """Clamp coefficients to reasonable chess domain bounds."""
    bounded = beta.copy()
    for idx, name in enumerate(TUNABLE_PARAM_NAMES):
        if name in PARAM_BOUNDS:
            lo, hi = PARAM_BOUNDS[name]
            bounded[idx] = np.clip(bounded[idx], lo, hi)
        elif "passed_pawn" in name:
            bounded[idx] = np.clip(bounded[idx], 0.0, 300.0)

    # Relative piece order check
    # queen >= rook + 200 >= bishop + 50 >= knight + 50
    pawn_mg = bounded[0]
    knight_mg = max(bounded[2], pawn_mg + 100.0)
    bishop_mg = max(bounded[4], knight_mg)
    rook_mg = max(bounded[6], bishop_mg + 50.0)
    queen_mg = max(bounded[8], rook_mg + 200.0)

    bounded[2] = knight_mg
    bounded[4] = bishop_mg
    bounded[6] = rook_mg
    bounded[8] = queen_mg
    return bounded


def compute_mae(
    X: np.ndarray,
    y: np.ndarray,
    fixed: np.ndarray,
    beta: np.ndarray,
) -> float:
    preds = X @ beta + fixed
    return float(np.mean(np.abs(y - preds)))


def tune_pipeline(
    npz_path: Path,
    method: str = "ridge",
    reg_lambda: float | None = None,
    output_path: Path | None = None,
) -> tuple[EvalParameters, dict[str, Any]]:
    data = np.load(npz_path)
    X_train = data["X_train"]
    y_train = data["y_train"]
    fixed_train = data["fixed_train"]

    X_val = data["X_val"]
    y_val = data["y_val"]
    fixed_val = data["fixed_val"]

    beta_0 = np.array(MW_0_2_EVAL.get_tunable_vector(), dtype=np.float32)
    baseline_val_mae = compute_mae(X_val, y_val, fixed_val, beta_0)

    # Lambda selection via validation MAE if not specified
    candidate_lambdas = [10.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0]
    candidate_deltas = [15.0, 25.0, 50.0] if method == "huber" else [100.0]
    best_delta = 25.0

    if reg_lambda is not None:
        best_lambda = reg_lambda
    else:
        best_lambda = 500.0
        best_val_mae = float("inf")
        for d in candidate_deltas:
            for lam in candidate_lambdas:
                if method == "ridge":
                    cand_beta = fit_ridge(X_train, y_train, fixed_train, beta_0, lam)
                else:
                    cand_beta = fit_huber(X_train, y_train, fixed_train, beta_0, lam, delta=d)
                cand_beta = enforce_sanity_bounds(cand_beta)
                val_mae = compute_mae(X_val, y_val, fixed_val, cand_beta)
                if val_mae < best_val_mae:
                    best_val_mae = val_mae
                    best_lambda = lam
                    best_delta = d

    # Final fit on train
    if method == "ridge":
        fitted_beta = fit_ridge(X_train, y_train, fixed_train, beta_0, best_lambda)
    else:
        fitted_beta = fit_huber(
            X_train, y_train, fixed_train, beta_0, best_lambda, delta=best_delta
        )

    bounded_beta = enforce_sanity_bounds(fitted_beta)
    tuned_val_mae = compute_mae(X_val, y_val, fixed_val, bounded_beta)

    # Convert to EvalParameters
    tuned_params = MW_0_2_EVAL.with_tunable_vector(bounded_beta.tolist())

    diff_report: list[dict[str, Any]] = []
    for name, b0, b_fit in zip(TUNABLE_PARAM_NAMES, beta_0, bounded_beta, strict=True):
        delta = float(b_fit - b0)
        pct = float((delta / b0 * 100.0) if abs(b0) > 1e-4 else 0.0)
        diff_report.append(
            {
                "parameter": name,
                "baseline": round(float(b0), 1),
                "tuned": round(float(b_fit), 1),
                "delta": round(float(delta), 1),
                "pct_change": round(float(pct), 1),
            }
        )

    summary: dict[str, Any] = {
        "method": method,
        "lambda": float(best_lambda),
        "baseline_val_mae": round(float(baseline_val_mae), 2),
        "tuned_val_mae": round(float(tuned_val_mae), 2),
        "val_mae_delta": round(float(tuned_val_mae - baseline_val_mae), 2),
        "diff_report": diff_report,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as out:
            json.dump(
                {
                    "summary": summary,
                    "parameters": tuned_params.to_dict(),
                },
                out,
                indent=2,
            )

    return tuned_params, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune MilkyWay evaluation coefficients.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("training/datasets/processed/dataset.npz"),
    )
    parser.add_argument("--method", choices=["ridge", "huber"], default="ridge")
    parser.add_argument("--reg-lambda", type=float, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("training/output/eval_coefficients.json"),
    )
    args = parser.parse_args()

    _tuned_params, summary = tune_pipeline(
        npz_path=args.dataset,
        method=args.method,
        reg_lambda=args.reg_lambda,
        output_path=args.output,
    )

    print(f"--- Fitting Results ({summary['method']}, lambda={summary['lambda']}) ---")
    print(
        f"Validation MAE: baseline={summary['baseline_val_mae']} -> "
        f"tuned={summary['tuned_val_mae']} (delta: {summary['val_mae_delta']})"
    )
    print("\nTop coefficient changes:")
    changes = sorted(summary["diff_report"], key=lambda r: abs(r["delta"]), reverse=True)
    for row in changes[:10]:
        param = row["parameter"]
        d_str = f"{row['delta']:+5.1f} ({row['pct_change']:+5.1f}%)"
        print(f"  {param:<24}: {row['baseline']:5.1f} -> {row['tuned']:5.1f} ({d_str})")


if __name__ == "__main__":
    main()
