"""Shared fixtures: an isolated copy of the audit corpus in a temp dir."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from alms_audit.schemas import default_root


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    src = default_root()
    for sub in ("spec", "configs", "fixtures"):
        shutil.copytree(src / sub, tmp_path / sub)
    return tmp_path
