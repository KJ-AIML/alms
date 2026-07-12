"""Runner + subprocess tests (DevSpec Sections 40 and 41)."""

from __future__ import annotations

import json
import sys

import pytest

from alms_audit.budget import BudgetError
from alms_audit.config import AuditConfig, load_config
from alms_audit.fixtures import load_fixtures
from alms_audit.lanes import load_lanes
from alms_audit.runner import RunError, run
from alms_audit.schemas import is_valid
from alms_audit.subprocess_runner import TIMEOUT_EXIT, run_probe


def _run(corpus_root, **kw):
    return run(
        run_id="testrun",
        fixtures=load_fixtures(corpus_root),
        lanes=load_lanes(corpus_root),
        config=load_config(corpus_root),
        root=corpus_root,
        **kw,
    )


def test_dry_run_is_default_and_writes_valid_manifest(corpus_root) -> None:
    summary = _run(corpus_root)
    assert summary.mode == "dry-run"
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert is_valid("run-manifest", manifest, corpus_root)
    assert manifest["credential_presence"]  # presence booleans recorded
    assert (summary.run_dir / "plan.json").is_file()


def test_live_without_confirm_is_refused(corpus_root) -> None:
    with pytest.raises(RunError):
        _run(corpus_root, live=True, confirm_live=False)


def test_live_without_budget_is_refused(corpus_root) -> None:
    no_budget = AuditConfig(None, None, 80, 256, 30000, 0)
    with pytest.raises(BudgetError):
        run(
            run_id="nb",
            fixtures=load_fixtures(corpus_root),
            lanes=load_lanes(corpus_root),
            config=no_budget,
            root=corpus_root,
            live=True,
            confirm_live=True,
        )


def test_live_gates_pass_but_no_probes_yet(corpus_root) -> None:
    # budget present + confirmed: gates pass, then refuses because probes are not built yet
    with pytest.raises(RunError, match="no runtime probes"):
        _run(corpus_root, live=True, confirm_live=True)


def test_subprocess_timeout_is_enforced(tmp_path) -> None:
    result = run_probe(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        timeout_ms=200,
        capture_dir=tmp_path / "raw",
    )
    assert result.timed_out
    assert result.exit_code == TIMEOUT_EXIT
    assert "timeout" in result.stderr_path.read_text(encoding="utf-8").lower()


def test_failed_run_preserves_diagnostics(tmp_path) -> None:
    result = run_probe(
        [sys.executable, "-c", "import sys; sys.stderr.write('boom happened'); sys.exit(3)"],
        timeout_ms=10000,
        capture_dir=tmp_path / "raw",
    )
    assert not result.timed_out
    assert result.exit_code == 3
    assert "boom happened" in result.stderr_path.read_text(encoding="utf-8")
