# ruff: noqa: E402
"""MilkyWay M17 — Student ONNX Export and Single-Core CPU Benchmark.

Exports distilled ChessPolicyStudent to ONNX format.
Validates:
  - ONNX runtime single-thread CPU latency (< 5ms target)
  - Model file size (< 50MB budget target)
  - Initialization / load time (< 1s target)
  - Numerical parity and top-k agreement with PyTorch
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import onnxruntime as ort  # type: ignore[import-untyped]
import torch

from training.data.representation import BOARD_SHAPE
from training.models.student import ChessPolicyStudent


def export_student_to_onnx(
    checkpoint_path: Path,
    output_onnx_path: Path,
) -> Path:
    """Export PyTorch student weights to ONNX format."""
    print(f"Loading student checkpoint from {checkpoint_path}...")
    student = ChessPolicyStudent()
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    student.load_state_dict(ckpt["model_state_dict"])
    student.eval()

    output_onnx_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_input = torch.randn(1, *BOARD_SHAPE, dtype=torch.float32)

    print(f"Exporting ONNX to {output_onnx_path}...")
    torch.onnx.export(
        student,
        (dummy_input,),
        str(output_onnx_path),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["board_planes"],
        output_names=["policy_logits"],
        dynamic_axes={
            "board_planes": {0: "batch_size"},
            "policy_logits": {0: "batch_size"},
        },
    )
    print(f"Export successful. File size: {output_onnx_path.stat().st_size / (1024 * 1024):.2f} MB")
    return output_onnx_path


def benchmark_onnx_cpu(
    onnx_path: Path,
    student_checkpoint: Path,
    num_iterations: int = 100,
) -> dict[str, float | int]:
    """Benchmark ONNX Runtime on single-core CPU and verify numerical parity."""
    # 1. Load time benchmark
    t0 = time.perf_counter()
    sess_opts = ort.SessionOptions()
    sess_opts.intra_op_num_threads = 1
    sess_opts.inter_op_num_threads = 1
    sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session = ort.InferenceSession(str(onnx_path), sess_opts, providers=["CPUExecutionProvider"])
    load_time_ms = (time.perf_counter() - t0) * 1000.0

    # 2. PyTorch reference
    torch.set_num_threads(1)
    student = ChessPolicyStudent()
    ckpt = torch.load(student_checkpoint, map_location="cpu")
    student.load_state_dict(ckpt["model_state_dict"])
    student.eval()

    test_input = np.random.randn(1, *BOARD_SHAPE).astype(np.float32)
    with torch.no_grad():
        pt_out = student(torch.from_numpy(test_input)).numpy()

    # ONNX inference
    input_name = session.get_inputs()[0].name
    onnx_out = session.run(None, {input_name: test_input})[0]

    # Parity check
    max_diff = float(np.max(np.abs(pt_out - onnx_out)))
    pt_top5 = np.argsort(pt_out[0])[::-1][:5]
    onnx_top5 = np.argsort(onnx_out[0])[::-1][:5]
    top5_match = bool(np.array_equal(pt_top5, onnx_top5))

    # Latency benchmark (single-core CPU)
    # Warmup
    for _ in range(10):
        _ = session.run(None, {input_name: test_input})

    start = time.perf_counter()
    for _ in range(num_iterations):
        _ = session.run(None, {input_name: test_input})
    total_time = time.perf_counter() - start
    avg_latency_ms = (total_time / num_iterations) * 1000.0

    size_mb = onnx_path.stat().st_size / (1024 * 1024)

    return {
        "file_size_mb": size_mb,
        "load_time_ms": load_time_ms,
        "single_inference_latency_ms": avg_latency_ms,
        "max_abs_diff": max_diff,
        "top5_agreement": top5_match,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export student to ONNX and benchmark.")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("training/checkpoints/student/best_student.pt"),
    )
    parser.add_argument("--output", type=Path, default=Path("weights/milkyway_policy.onnx"))
    parser.add_argument("--benchmark-iters", type=int, default=100)
    args = parser.parse_args()

    export_student_to_onnx(args.checkpoint, args.output)
    results = benchmark_onnx_cpu(args.output, args.checkpoint, num_iterations=args.benchmark_iters)

    print("\n=== Single-Core CPU ONNX Benchmark ===")
    print(f"File size:            {results['file_size_mb']:.2f} MB")
    print(f"Load time:            {results['load_time_ms']:.1f} ms (budget < 1000 ms)")
    lat = results["single_inference_latency_ms"]
    print(f"Single eval latency:  {lat:.2f} ms (budget < 5.0 ms)")
    print(f"Max absolute diff:    {results['max_abs_diff']:.6e}")
    print(f"Top-5 ranking match:  {results['top5_agreement']}")


if __name__ == "__main__":
    main()
