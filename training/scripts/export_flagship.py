# ruff: noqa: E402
"""Export the flagship joint policy+value net to dual-output ONNX.

Verifies output names (policy_logits, value), numerical parity for both
heads, file size, load time, and single-core CPU latency.

  training/.venv/Scripts/python.exe training/scripts/export_flagship.py \
      --checkpoint training/checkpoints/flagship_v2/best_flagship.pt \
      --output weights/milkyway_flagship.onnx
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
from training.models.flagship import ChessFlagshipNet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--benchmark-iters", type=int, default=100)
    args = parser.parse_args()

    net = ChessFlagshipNet()
    ckpt = torch.load(args.checkpoint, map_location="cpu")
    net.load_state_dict(ckpt["model_state_dict"])
    net.eval()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    dummy = torch.randn(1, *BOARD_SHAPE)
    torch.onnx.export(
        net,
        (dummy,),
        str(args.output),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
        input_names=["board_planes"],
        output_names=["policy_logits", "value"],
        dynamic_axes={
            "board_planes": {0: "batch_size"},
            "policy_logits": {0: "batch_size"},
            "value": {0: "batch_size"},
        },
    )
    size_mb = args.output.stat().st_size / (1024 * 1024)
    print(f"exported {size_mb:.2f} MB -> {args.output}")

    torch.set_num_threads(1)
    sess_opts = ort.SessionOptions()
    sess_opts.intra_op_num_threads = 1
    sess_opts.inter_op_num_threads = 1
    sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    t0 = time.perf_counter()
    session = ort.InferenceSession(str(args.output), sess_opts, providers=["CPUExecutionProvider"])
    print(f"load time: {(time.perf_counter() - t0) * 1000:.0f} ms")
    test = np.random.randn(1, *BOARD_SHAPE).astype(np.float32)
    names = [o.name for o in session.get_inputs()]
    on_pol, on_val = session.run(None, {names[0]: test})
    with torch.no_grad():
        ref_pol, ref_val = net(torch.from_numpy(test))
    print(f"policy max diff: {float(np.abs(ref_pol.numpy() - on_pol).max()):.2e}")
    print(f"value max diff:  {float(np.abs(ref_val.numpy() - on_val).max()):.2e}")
    for _ in range(10):
        session.run(None, {names[0]: test})
    t0 = time.perf_counter()
    for _ in range(args.benchmark_iters):
        session.run(None, {names[0]: test})
    ms = (time.perf_counter() - t0) / args.benchmark_iters * 1000
    print(f"single inference latency: {ms:.2f} ms (joint policy+value)")


if __name__ == "__main__":
    main()
