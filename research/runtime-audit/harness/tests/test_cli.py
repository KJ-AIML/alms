"""P0.1 CLI tests: validate/list-fixtures/list-lanes, incl. Windows paths with spaces."""

from __future__ import annotations

import shutil
from pathlib import Path

from alms_audit.cli import main
from alms_audit.schemas import default_root

_OVERRIDE = "configs/first-live.override.toml"


def test_validate_passes_on_committed_corpus() -> None:
    assert main(["validate"]) == 0


def test_list_fixtures_lists_examples(capsys) -> None:
    assert main(["list-fixtures"]) == 0
    out = capsys.readouterr().out
    assert "GEN-001" in out
    assert "STR-001" in out


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


def test_plan_previews_without_calls(capsys) -> None:
    assert main(["plan"]) == 0
    out = capsys.readouterr().out
    assert "expected live call count" in out
    assert "no live calls were made" in out


def test_run_dry_run_default(corpus_root: Path, capsys) -> None:
    assert main(["run", "--root", str(corpus_root), "--run-id", "clirun"]) == 0
    out = capsys.readouterr().out
    assert "mode: dry-run" in out
    assert (corpus_root / "runs" / "clirun" / "run-manifest.json").is_file()


def test_run_live_without_confirm_is_refused(corpus_root: Path, capsys) -> None:
    assert main(["run", "--root", str(corpus_root), "--live"]) == 2
    assert "REFUSED" in capsys.readouterr().out


def _cfg(corpus_root: Path) -> str:
    return str(corpus_root / _OVERRIDE)


def test_run_execute_missing_config_refused(corpus_root: Path, capsys) -> None:
    assert (
        main(
            [
                "run",
                "--root",
                str(corpus_root),
                "--offline-execute",
                "--lane",
                "openai-native",
                "--model",
                "gpt-5.4-nano",
                "--fixtures",
                "GEN-001",
            ]
        )
        == 2
    )
    assert "missing configuration" in capsys.readouterr().out


def test_run_unknown_config_path_refused(corpus_root: Path, capsys) -> None:
    assert (
        main(
            [
                "run",
                "--root",
                str(corpus_root),
                "--offline-execute",
                "--config",
                str(corpus_root / "nope.toml"),
                "--lane",
                "openai-native",
                "--model",
                "gpt-5.4-nano",
                "--fixtures",
                "GEN-001",
            ]
        )
        == 2
    )
    assert "unknown configuration path" in capsys.readouterr().out


def test_run_unapproved_fixture_refused_before_launch(corpus_root: Path, capsys) -> None:
    # Selection fails before any subprocess, so this is fast and creates no evidence.
    assert (
        main(
            [
                "run",
                "--root",
                str(corpus_root),
                "--offline-execute",
                "--config",
                _cfg(corpus_root),
                "--lane",
                "openai-native",
                "--model",
                "gpt-5.4-nano",
                "--fixtures",
                "GEN-001,ERROR-001",
            ]
        )
        == 2
    )
    assert "approved first-live" in capsys.readouterr().out
    assert not (corpus_root / "runs").exists()


def test_run_offline_execute_full_pipeline_via_cli(capsys) -> None:
    """Drives the real subprocess against the real probe env; cleans up its run dir."""
    root = default_root()
    run_id = "cli-wire-test-001"
    run_dir = root / "runs" / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    try:
        code = main(
            [
                "run",
                "--config",
                str(root / _OVERRIDE),
                "--lane",
                "openai-native",
                "--model",
                "gpt-5.4-nano",
                "--offline-execute",
                "--run-id",
                run_id,
                "--fixtures",
                "GEN-001,ROLE-001,STR-001,TOOL-001,STREAM-001,USAGE-001",
            ]
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "mode: offline" in out
        for fx in ("GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"):
            assert f"fixture {fx}:" in out
        assert (run_dir / "run-summary.json").is_file()
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)


def test_validate_fails_on_bad_fixture(tmp_path: Path, capsys) -> None:
    root = default_root()
    spaced = tmp_path / "broken corpus"
    shutil.copytree(root / "spec", spaced / "spec")
    shutil.copytree(root / "configs", spaced / "configs")
    (spaced / "fixtures" / "generation").mkdir(parents=True)
    (spaced / "fixtures" / "generation" / "bad.json").write_text('{"id": "x"}', encoding="utf-8")
    assert main(["validate", "--root", str(spaced)]) == 1
    assert "FAIL" in capsys.readouterr().out
