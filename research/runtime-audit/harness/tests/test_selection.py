"""Run selection + validation tests (DevSpec Section 39)."""

from __future__ import annotations

import pytest

from alms_audit.config import approved_fixtures, load_raw
from alms_audit.fixtures import load_fixtures
from alms_audit.lanes import load_lanes
from alms_audit.schemas import default_root
from alms_audit.selection import (
    SelectionError,
    parse_fixture_ids,
    resolve_model,
    select_fixtures,
    select_lane,
)

_APPROVED = ["GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"]


def _fixtures():
    return load_fixtures(default_root())


def _openai_lane():
    return select_lane(load_lanes(default_root()), "openai-native")


def test_parse_fixture_ids_preserves_order():
    assert parse_fixture_ids("TOOL-001, GEN-001,STR-001") == ["TOOL-001", "GEN-001", "STR-001"]


def test_parse_fixture_ids_rejects_empty():
    with pytest.raises(SelectionError):
        parse_fixture_ids("  ,  ")


def test_parse_fixture_ids_rejects_duplicates():
    with pytest.raises(SelectionError, match="duplicate"):
        parse_fixture_ids("GEN-001,GEN-001")


def test_select_lane_unknown_rejected():
    with pytest.raises(SelectionError, match="unknown lane"):
        select_lane(load_lanes(default_root()), "does-not-exist")


def test_select_lane_missing_rejected():
    with pytest.raises(SelectionError):
        select_lane(load_lanes(default_root()), None)


def test_resolve_model_required():
    with pytest.raises(SelectionError, match="model"):
        resolve_model(_openai_lane(), None)


def test_resolve_model_binds_explicit_model():
    lane = resolve_model(_openai_lane(), "gpt-5.4-nano-2026-03-17")
    assert lane["model"] == "gpt-5.4-nano-2026-03-17"
    assert lane["lane_id"] == "openai-native"


def test_select_fixtures_unknown_rejected():
    with pytest.raises(SelectionError, match="unknown fixture"):
        select_fixtures(_fixtures(), ["NOPE-999"], lane=_openai_lane())


def test_select_fixtures_preserves_requested_order():
    ids = ["STR-001", "GEN-001", "TOOL-001"]
    got = select_fixtures(_fixtures(), ids, lane=_openai_lane(), approved_fixtures=_APPROVED)
    assert [fx.id for fx in got] == ids


def test_unapproved_first_live_fixture_rejected():
    with pytest.raises(SelectionError, match="approved first-live"):
        select_fixtures(
            _fixtures(), ["GEN-001", "ERROR-001"], lane=_openai_lane(), approved_fixtures=_APPROVED
        )


def test_ineligible_capability_rejected():
    # EMBED-001 declares the embeddings capability, unsupported by the openai-native probe.
    with pytest.raises(SelectionError, match="does not support"):
        select_fixtures(_fixtures(), ["EMBED-001"], lane=_openai_lane())


def test_approved_set_loads_from_first_live_config():
    data = load_raw(default_root() / "configs" / "first-live.override.toml")
    assert approved_fixtures(data) == _APPROVED
    # The default config declares no restriction.
    assert approved_fixtures(load_raw(default_root() / "configs" / "audit.default.toml")) is None
