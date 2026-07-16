"""P0.7D fixture-lint tests (DevSpec Tier 0 / Sections 21, 44, 79)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from alms_audit.cli import main
from alms_audit.fixture_lint import lint_fixtures
from alms_audit.schemas import default_root


def test_committed_corpus_passes_fixture_lint() -> None:
    report = lint_fixtures()
    assert report.ok, [(i.fixture_id, i.message) for i in report.issues]


def test_planted_invalid_fixture_fails_schema(corpus_root: Path) -> None:
    bad = corpus_root / "fixtures" / "generation" / "bad.json"
    bad.write_text('{"id": "BAD-001"}', encoding="utf-8")
    report = lint_fixtures(corpus_root, reference_root=default_root())
    assert not report.ok
    assert any("schema" in i.message for i in report.issues)


def test_duplicate_id_fails(corpus_root: Path) -> None:
    src = corpus_root / "fixtures" / "generation" / "GEN-001.json"
    shutil.copyfile(src, corpus_root / "fixtures" / "generation" / "GEN-001-copy.json")
    report = lint_fixtures(corpus_root, reference_root=default_root())
    assert not report.ok
    assert any("duplicate" in i.message for i in report.issues)


def test_empty_expected_invariants_fails(corpus_root: Path) -> None:
    path = corpus_root / "fixtures" / "generation" / "GEN-001.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["expected_invariants"] = {}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    report = lint_fixtures(corpus_root, reference_root=default_root())
    assert not report.ok
    assert any("expected_invariants" in i.message for i in report.issues)


def test_unknown_invariant_key_fails(corpus_root: Path) -> None:
    path = corpus_root / "fixtures" / "generation" / "GEN-001.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["expected_invariants"]["__bogus_invariant__"] = True
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    report = lint_fixtures(corpus_root, reference_root=default_root())
    assert not report.ok
    assert any("unknown invariant" in i.message for i in report.issues)


def test_lint_fixtures_cli(capsys) -> None:
    assert main(["lint-fixtures"]) == 0
    out = capsys.readouterr().out
    assert "PASS fixture lint" in out
    assert "fixture(s)" in out
