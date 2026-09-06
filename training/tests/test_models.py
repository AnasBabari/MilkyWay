"""Unit tests for Teacher, Student, and MultiTask Loss."""

from __future__ import annotations

import torch

from training.models.losses import MultiTaskChessLoss
from training.models.student import ChessPolicyStudent
from training.models.teacher import create_teacher


def test_teacher_forward_shapes_and_params() -> None:
    for name in ("teacher_a", "teacher_b", "teacher_c", "teacher_d"):
        teacher = create_teacher(name)
        params = teacher.count_parameters()
        assert params > 1_000_000, f"{name} should have > 1M params, got {params}"

        dummy_x = torch.randn(4, 18, 8, 8)
        p_log, w_log, val = teacher(dummy_x)

        assert p_log.shape == (4, 1968)
        assert w_log.shape == (4, 3)
        assert val.shape == (4, 1)
        assert torch.all(val >= -1.0) and torch.all(val <= 1.0)


def test_student_forward_and_params() -> None:
    student = ChessPolicyStudent()
    params = student.count_parameters()
    # Student target: ~0.5M - 2.0M parameters
    assert 500_000 <= params <= 2_500_000, f"Student params out of range: {params}"

    dummy_x = torch.randn(2, 18, 8, 8)
    p_log = student(dummy_x)
    assert p_log.shape == (2, 1968)


def test_multi_task_loss_backward() -> None:
    teacher = create_teacher("teacher_a")
    loss_fn = MultiTaskChessLoss()

    batch_size = 4
    x = torch.randn(batch_size, 18, 8, 8, requires_grad=False)
    p_log, w_log, val = teacher(x)

    batch = {
        "policy_idx": torch.tensor([10, 20, 30, 40], dtype=torch.long),
        "policy_mask": torch.tensor([1.0, 1.0, 0.0, 1.0]),
        "wdl": torch.tensor([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.5, 0.5, 0.0], [0.0, 0.0, 1.0]]),
        "wdl_mask": torch.tensor([1.0, 1.0, 1.0, 0.0]),
        "value": torch.tensor([0.5, -0.2, 0.0, 0.9]),
        "value_mask": torch.tensor([1.0, 0.0, 1.0, 1.0]),
    }

    loss_dict = loss_fn(p_log, w_log, val, batch)
    assert "loss" in loss_dict
    assert loss_dict["loss"].item() > 0

    loss_dict["loss"].backward()
    # Verify gradients computed
    first_weight = next(teacher.parameters())
    assert first_weight.grad is not None
