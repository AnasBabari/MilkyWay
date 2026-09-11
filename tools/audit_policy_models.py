"""Compare existing team-trained root policies on a fixed validation sample."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data_path = root / "training/datasets/master_value_v2/val/shard_00000.npz"
    with np.load(data_path) as data:
        eligible = np.flatnonzero(data["policy_masks"])
        indices = np.random.default_rng(20260909).choice(eligible, min(512, len(eligible)),
                                                       replace=False)
        x = data["boards"][indices].astype(np.float32)
        target = data["policy_indices"][indices]
    models = ["experiments/silky_snow/weights/milkyway_policy.onnx",
              "experiments/astralix/r1_policy/weights/milkyway_astralix.onnx",
              "weights/milkyway_flagship_v6.onnx"]
    reports = []
    for name in models:
        path = root / name
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
        output = session.get_outputs()[0].name
        input_name = session.get_inputs()[0].name
        predictions = np.concatenate([session.run([output], {input_name: row[None]})[0]
                                      for row in x])
        assert predictions.shape == (len(x), 1968) and np.isfinite(predictions).all()
        ranks = (predictions > predictions[np.arange(len(x)), target, None]).sum(axis=1)
        reports.append({"model": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "top1": float((ranks == 0).mean()), "top5": float((ranks < 5).mean())})
    report = {"validation_source_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
              "indices": indices.tolist(), "models": reports,
              "interpretation": "unmasked agreement with played-move labels; reused validation, "
                                "not strength evidence or independent holdout"}
    output_path = root / "experiments/compact_cycle_01/policy_audit.json"
    output_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
