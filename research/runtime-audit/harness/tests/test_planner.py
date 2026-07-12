"""Planner tests (DevSpec Sections 39 and 45): full matrix, every skip explained."""

from __future__ import annotations

from alms_audit.environment import provider_env_var
from alms_audit.fixtures import load_fixtures
from alms_audit.lanes import load_lanes
from alms_audit.planner import build_plan


def _live_count(fixtures) -> int:
    return sum(1 for f in fixtures if f.live_required)


def test_dry_run_plans_every_pair_with_no_skips(corpus_root) -> None:
    fixtures = load_fixtures(corpus_root)
    lanes = load_lanes(corpus_root)
    plan = build_plan(fixtures, lanes, live=False)
    assert len(plan.entries) == len(fixtures) * len(lanes)
    assert plan.skipped == []
    # only live-required fixtures would consume a call
    assert plan.expected_call_count == _live_count(fixtures) * len(lanes)


def test_live_plan_skips_live_required_pairs_with_missing_credentials(corpus_root) -> None:
    fixtures = load_fixtures(corpus_root)
    lanes = load_lanes(corpus_root)
    plan = build_plan(fixtures, lanes, live=True, credentials={})  # no creds present
    # every skip is a live-required pair; anything still planned must be non-calling
    assert plan.skipped
    for e in plan.skipped:
        assert "missing credential" in e.skip_reason
    assert all(not e.will_call for e in plan.planned)


def test_live_plan_with_credentials_present(corpus_root) -> None:
    fixtures = load_fixtures(corpus_root)
    lanes = load_lanes(corpus_root)
    providers = {ln["provider"] for ln in lanes}
    creds = {provider_env_var(p): True for p in providers}
    plan = build_plan(fixtures, lanes, live=True, credentials=creds)
    assert plan.skipped == []
    assert plan.expected_call_count == _live_count(fixtures) * len(lanes)
