"""Pytest root configuration.

Ensures PyTorch loads its DLLs before conflicting plugins (e.g. pytest-qt / PyQt5)
under Windows Python 3.14.
"""

from __future__ import annotations

import contextlib

with contextlib.suppress(ImportError):
    import torch  # noqa: F401
