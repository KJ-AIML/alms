"""Corpus-level tests for the P0.3 fixture corpus (DevSpec Sections 56-58)."""

from __future__ import annotations

import shutil
from pathlib import Path

from alms_audit.cli import main
from alms_audit.fixtures import duplicate_ids, load_fixtures
from alms_audit.schemas import is_valid, validation_errors

FEATURES = {
    "generation",
    "roles",
    "structured_output",
    "tools",
    "streaming",
    "cancellation",
    "timeout",
    "retry",
    "errors",
    "usage",
    "embeddings",
    "multimodal",
}
RESULT_STATUSES = {
    "PASS",
    "PASS_WITH_EXTENSION",
    "UNSUPPORTED_DECLARED",
    "UNSUPPORTED_OBSERVED",
    "BLOCKED_CONFIGURATION",
    "FAIL_INVARIANT",
    "ERROR_RUNTIME",
    "INCONCLUSIVE",
}
TIERS = {"BASE", "STRESS", "OPTIONAL"}
COST_CLASSES = {"offline", "live_core", "live_stress"}
FORBIDDEN_PROSE_KEYS = {
    "exact_text",
    "expected_text",
    "response_equals",
    "exact_response",
    "assistant_text_equals",
}
# Canonical minimum IDs the slice must cover (DevSpec Section 57).
CANONICAL_MIN = {
    "GEN-001",
    "ROLE-001",
    "STR-001",
    "STR-004",
    "STR-005",
    "TOOL-001",
    "TOOL-004",
    "STREAM-001",
    "STREAM-002",
    "CANCEL-001",
    "TIMEOUT-001",
    "RETRY-001",
    "USAGE-002",
    "EMBED-001",
    "MM-001",
}


def test_all_fixtures_validate() -> None:
    fixtures = load_fixtures()
    assert fixtures, "expected fixtures on disk"
    for f in fixtures:
        assert is_valid("fixture", f.data), (f.id, validation_errors("fixture", f.data))


def test_fixture_ids_unique() -> None:
    fixtures = load_fixtures()
    assert duplicate_ids(fixtures) == []
    assert len({f.id for f in fixtures}) == len(fixtures)


def test_categories_and_tiers_valid() -> None:
    for f in load_fixtures():
        assert f.feature in FEATURES, f.id
        assert f.tier in TIERS, f.id
        assert f.cost_class in COST_CLASSES, f.id


def test_live_and_cost_flags_consistent() -> None:
    for f in load_fixtures():
        assert isinstance(f.data["requirements"]["live_required"], bool), f.id
        if f.cost_class == "offline":
            assert f.live_required is False, f.id  # offline cost implies no live call


def test_allowed_outcomes_valid_and_nonempty() -> None:
    for f in load_fixtures():
        ao = f.data["allowed_outcomes"]
        assert ao, f.id
        assert set(ao) <= RESULT_STATUSES, f.id


def test_raw_evidence_distinct_from_normalization() -> None:
    """Raw evidence requirements must stay distinct from normalization requirements."""
    for f in load_fixtures():
        ev = f.data["evidence_requirements"]
        assert ev["raw"] and ev["normalized"], f.id
        assert set(ev["raw"]) != set(ev["normalized"]), f.id


def test_no_exact_prose_invariant() -> None:
    for f in load_fixtures():
        keys = set(f.data["expected_invariants"].keys())
        assert not (keys & FORBIDDEN_PROSE_KEYS), (f.id, keys & FORBIDDEN_PROSE_KEYS)


def test_unsupported_outcomes_explicit_where_expected() -> None:
    by_id = {f.id: f for f in load_fixtures()}
    for fid in ("STR-004", "TOOL-004", "STREAM-002", "EMBED-001", "MM-001"):
        outcomes = set(by_id[fid].data["allowed_outcomes"])
        assert any(o.startswith("UNSUPPORTED") for o in outcomes), fid


def test_canonical_minimum_ids_present() -> None:
    ids = {f.id for f in load_fixtures()}
    assert CANONICAL_MIN <= ids, CANONICAL_MIN - ids


def test_corpus_validates_via_cli() -> None:
    assert main(["validate"]) == 0


def test_duplicate_id_fails_validation(corpus_root: Path, capsys) -> None:
    src = corpus_root / "fixtures" / "generation" / "GEN-001.json"
    shutil.copyfile(src, corpus_root / "fixtures" / "generation" / "GEN-001-copy.json")
    assert main(["validate", "--root", str(corpus_root)]) == 1
    assert "duplicate" in capsys.readouterr().out.lower()


def test_listing_is_deterministic(capsys) -> None:
    assert main(["list-fixtures"]) == 0
    first = capsys.readouterr().out
    assert main(["list-fixtures"]) == 0
    second = capsys.readouterr().out
    assert first == second
    assert first.strip()  # non-empty


def test_list_fixtures_tier_filter(capsys) -> None:
    assert main(["list-fixtures", "--tier", "BASE"]) == 0
    out = capsys.readouterr().out
    assert "GEN-001" in out
    assert "CANCEL-001" not in out  # STRESS tier excluded
