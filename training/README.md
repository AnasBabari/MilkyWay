# MilkyWay M17 — Offline GPU Training Infrastructure

This directory contains offline training and dataset infrastructure for MilkyWay M17.

## Structure
- `configs/`: Experiment configuration files
- `data/`: Board representations, move vocabulary, dataset schemas, sharding, and PGN loaders
- `models/`: Teacher ResNet models, student distillation models, loss functions
- `scripts/`: GPU benchmark, training, distillation, and ONNX export scripts
- `metrics/`: Validation metrics, benchmark evaluation suites, failure position suites
- `tests/`: Isolated unit and integration tests for training pipeline

## Isolation
This infrastructure is strictly offline. Training dependencies and intermediate artifacts
(checkpoints, large raw datasets, external binaries) are isolated and gitignored.
Only validated, exported runtime weights (`weights/milkyway_policy.onnx`) and the
single-core CPU ONNX inference wrapper are eligible to ship.
