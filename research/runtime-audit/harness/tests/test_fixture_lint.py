"""P0.7D/P0.7E fixture-lint tests (DevSpec Tier 0 / Sections 21, 44, 79; P0.3 acceptance)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from alms_audit.cli import main
from alms_audit.fixture_lint import (
    DEVSPEC_EVALUATORS,
    MANUAL_REVIEW,
    PENDING_EVALUATORS,
    allowed_invariant_keys,
    corpus_invariant_keys,
    lint_fixtures,
)
from alms_audit.fixtures import load_fixtures
from alms_audit.invariants.registry import EVALUATORS
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


def test_allowed_keys_exclude_silent_corpus_union() -> None:
    """P0.3: every non-deterministic key must be explicit PENDING or MANUAL_REVIEW."""
    allowed = allowed_invariant_keys()
    assert allowed == (DEVSPEC_EVALUATORS | PENDING_EVALUATORS | MANUAL_REVIEW)
    # Corpus keys must not sneak in solely by appearing in fixtures/.
    assert "__corpus_only_silent__" not in allowed


def test_corpus_keys_are_explicitly_classified() -> None:
    keys = corpus_invariant_keys(load_fixtures())
    for key in keys:
        if key in EVALUATORS or key in DEVSPEC_EVALUATORS:
            continue
        assert key in PENDING_EVALUATORS or key in MANUAL_REVIEW, (
            f"{key} lacks explicit PENDING_EVALUATORS or MANUAL_REVIEW marker"
        )


def test_provider_specific_syntax_fails(corpus_root: Path) -> None:
    path = corpus_root / "fixtures" / "generation" / "GEN-001.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["intent"] = "Call openai.responses.create with ChatOpenAI.invoke"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    report = lint_fixtures(corpus_root)
    assert not report.ok
    assert any("provider-specific" in i.message for i in report.issues)


def test_unknown_capability_fails(corpus_root: Path) -> None:
    path = corpus_root / "fixtures" / "generation" / "GEN-001.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["requirements"]["capabilities"] = ["not_a_real_capability"]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    report = lint_fixtures(corpus_root)
    assert not report.ok
    assert any("capability" in i.message for i in report.issues)


def test_offline_cost_class_requires_live_required_false(corpus_root: Path) -> None:
    path = corpus_root / "fixtures" / "generation" / "GEN-001.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["cost_class"] = "offline"
    data["requirements"]["live_required"] = True
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    report = lint_fixtures(corpus_root)
    assert not report.ok
    assert any("live_required" in i.message and "offline" in i.message for i in report.issues)


def test_devspec_evaluators_match_registry() -> None:
    assert set(EVALUATORS) == set(DEVSPEC_EVALUATORS)
