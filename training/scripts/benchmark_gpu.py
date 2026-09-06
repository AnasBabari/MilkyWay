# ruff: noqa: E402
"""MilkyWay M17 — GPU Saturation and Throughput Benchmark.

Sweeps model architectures, batch sizes, AMP settings, and measures:
  - Throughput (samples/sec)
  - VRAM allocated and reserved (MB)
  - Step time (ms)
  - GPU utilization / memory stats
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
from torch.amp.autocast_mode import autocast
from torch.amp.grad_scaler import GradScaler

from training.models.losses import MultiTaskChessLoss
from training.models.teacher import create_teacher


def benchmark_configuration(
    arch_name: str,
    batch_size: int,
    use_amp: bool = True,
    warmup_steps: int = 5,
    benchmark_steps: int = 20,
    device: str = "cuda",
) -> dict[str, float | int | str] | None:
    """Benchmark forward+backward pass for a single configuration."""
    if not torch.cuda.is_available() and device == "cuda":
        print("CUDA is not available, cannot run GPU benchmark", file=sys.stderr)
        return None

    # Clear memory
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    dev = torch.device(device)
    model = create_teacher(arch_name).to(dev)
    model.train()

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    loss_fn = MultiTaskChessLoss()
    scaler = GradScaler("cuda", enabled=use_amp)

    # Synthetic batch on device
    dummy_boards = torch.randn(batch_size, 18, 8, 8, device=dev)
    dummy_batch = {
        "policy_idx": torch.randint(0, 1968, (batch_size,), device=dev, dtype=torch.long),
        "policy_mask": torch.ones(batch_size, device=dev),
        "wdl": torch.full((batch_size, 3), 1.0 / 3.0, device=dev),
        "wdl_mask": torch.ones(batch_size, device=dev),
        "value": torch.zeros(batch_size, device=dev),
        "value_mask": torch.ones(batch_size, device=dev),
    }

    # Warmup
    try:
        for _ in range(warmup_steps):
            optimizer.zero_grad(set_to_none=True)
            with autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                p_log, w_log, val = model(dummy_boards)
                loss_dict = loss_fn(p_log, w_log, val, dummy_batch)
                loss = loss_dict["loss"]

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

        torch.cuda.synchronize()

        # Benchmark timing
        start_time = time.perf_counter()
        for _ in range(benchmark_steps):
            optimizer.zero_grad(set_to_none=True)
            with autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                p_log, w_log, val = model(dummy_boards)
                loss_dict = loss_fn(p_log, w_log, val, dummy_batch)
                loss = loss_dict["loss"]

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

        torch.cuda.synchronize()
        total_time = time.perf_counter() - start_time
    except torch.cuda.OutOfMemoryError:
        gc.collect()
        torch.cuda.empty_cache()
        return {
            "arch": arch_name,
            "batch_size": batch_size,
            "amp": use_amp,
            "status": "OOM",
            "samples_per_sec": 0.0,
            "step_time_ms": 0.0,
            "peak_vram_mb": 0.0,
        }

    step_time = total_time / benchmark_steps
    samples_per_sec = (batch_size * benchmark_steps) / total_time
    peak_vram_mb = torch.cuda.max_memory_allocated(dev) / (1024 * 1024)

    return {
        "arch": arch_name,
        "batch_size": batch_size,
        "amp": use_amp,
        "status": "OK",
        "samples_per_sec": samples_per_sec,
        "step_time_ms": step_time * 1000.0,
        "peak_vram_mb": peak_vram_mb,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="MilkyWay GPU saturation benchmark.")
    parser.add_argument(
        "--architectures",
        nargs="+",
        default=["teacher_a", "teacher_b", "teacher_c"],
        help="Architectures to test",
    )
    parser.add_argument(
        "--batch-sizes",
        nargs="+",
        type=int,
        default=[128, 256, 512, 1024],
        help="Batch sizes to sweep",
    )
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print("CUDA is unavailable. Cannot run GPU benchmark.")
        sys.exit(1)

    gpu_name = torch.cuda.get_device_name(0)
    total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    print("=== MilkyWay M17 GPU Benchmark ===")
    print(f"GPU: {gpu_name} ({total_vram_gb:.2f} GB Total VRAM)\n")

    results: list[dict[str, float | int | str]] = []
    header = (
        f"{'Model':<12} | {'Batch':<6} | {'AMP':<5} | {'Status':<6} | "
        f"{'Samples/s':<11} | {'Step (ms)':<10} | {'Peak VRAM':<10}"
    )
    print(header)
    print("-" * 75)

    for arch in args.architectures:
        for bsz in args.batch_sizes:
            res = benchmark_configuration(arch, bsz, use_amp=True)
            if res is None:
                continue
            results.append(res)
            if res["status"] == "OOM":
                row_oom = (
                    f"{res['arch']:<12} | {res['batch_size']:<6} | {res['amp']!s:<5} | "
                    f"{'OOM':<6} | {'-':<11} | {'-':<10} | {'-':<10}"
                )
                print(row_oom)
                break  # Don't try larger batches for this architecture
            else:
                row_ok = (
                    f"{res['arch']:<12} | {res['batch_size']:<6} | {res['amp']!s:<5} | {'OK':<6} | "
                    f"{res['samples_per_sec']:<11.1f} | {res['step_time_ms']:<10.2f} | "
                    f"{res['peak_vram_mb']:<8.1f} MB"
                )
                print(row_ok)

    # Also test AMP off comparison on best batch for reference
    print("\nComparing AMP On vs AMP Off on Teacher B (Batch 512):")
    res_amp = benchmark_configuration("teacher_b", 512, use_amp=True)
    res_noamp = benchmark_configuration("teacher_b", 512, use_amp=False)
    if res_amp and res_noamp:
        s_amp = (
            f"AMP On:  {res_amp['samples_per_sec']:.1f} samples/s, "
            f"VRAM: {res_amp['peak_vram_mb']:.1f} MB"
        )
        s_noamp = (
            f"AMP Off: {res_noamp['samples_per_sec']:.1f} samples/s, "
            f"VRAM: {res_noamp['peak_vram_mb']:.1f} MB"
        )
        print(s_amp)
        print(s_noamp)


if __name__ == "__main__":
    main()
