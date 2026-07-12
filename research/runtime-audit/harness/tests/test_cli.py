"""P0.1 CLI tests: validate/list-fixtures/list-lanes, incl. Windows paths with spaces."""

from __future__ import annotations

import shutil
from pathlib import Path

from alms_audit.cli import main
from alms_audit.schemas import default_root


def test_validate_passes_on_committed_corpus() -> None:
    assert main(["validate"]) == 0


def test_list_fixtures_lists_examples(capsys) -> None:
    assert main(["list-fixtures"]) == 0
    out = capsys.readouterr().out
    assert "generation-basic-001" in out
    assert "structured-person-001" in out


def test_list_lanes_lists_canonical_lanes(capsys) -> None:
    assert main(["list-lanes"]) == 0
    out = capsys.readouterr().out
    assert "openai-native" in out
    assert "langchain-openai" in out


def test_validate_with_root_path_containing_spaces(tmp_path: Path) -> None:
    """Acceptance: CLI works on Windows paths with spaces (DevSpec P0.1)."""
    root = default_root()
    spaced = tmp_path / "audit lab dir"
    for sub in ("spec", "fixtures", "configs"):
        shutil.copytree(root / sub, spaced / sub)
    assert " " in str(spaced)
    assert main(["validate", "--root", str(spaced)]) == 0


def test_validate_fails_on_bad_fixture(tmp_path: Path, capsys) -> None:
    root = default_root()
    spaced = tmp_path / "broken corpus"
    shutil.copytree(root / "spec", spaced / "spec")
    shutil.copytree(root / "configs", spaced / "configs")
    (spaced / "fixtures" / "generation").mkdir(parents=True)
    (spaced / "fixtures" / "generation" / "bad.json").write_text('{"id": "x"}', encoding="utf-8")
    assert main(["validate", "--root", str(spaced)]) == 1
    assert "FAIL" in capsys.readouterr().out
