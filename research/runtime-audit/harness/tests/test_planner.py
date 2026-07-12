"""Planner tests (DevSpec Sections 39 and 45): full matrix, every skip explained."""

from __future__ import annotations

from pathlib import Path

from alms_audit.config import load_config_path, load_raw
from alms_audit.environment import provider_env_var
from alms_audit.fixtures import load_fixtures
from alms_audit.lanes import load_lanes
from alms_audit.pricing import load_snapshots
from alms_audit.planner import build_live_plan, build_plan
from alms_audit.selection import resolve_model, select_fixtures, select_lane


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


# --- LivePlan (bounded single-lane execution matrix) ---

_APPROVED = ["GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"]


def _live_plan(corpus_root, mode: str, creds: dict):
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    config = load_config_path(cfg_path)
    pricing = load_snapshots(load_raw(cfg_path)).get("gpt-5.4-nano")
    lane = resolve_model(select_lane(load_lanes(corpus_root), "openai-native"), "gpt-5.4-nano")
    fixtures = select_fixtures(
        load_fixtures(corpus_root), _APPROVED, lane=lane, approved_fixtures=_APPROVED
    )
    return build_live_plan(
        mode=mode,
        lane=lane,
        model="gpt-5.4-nano",
        fixtures=fixtures,
        config=config,
        credentials=creds,
        run_dir=corpus_root / "runs" / "r1",
        probe_project_dir=Path("probes/openai-native"),
        probe_run_command=["uv", "run"],
        pricing=pricing,
    )


def test_live_plan_offline_all_six_call_no_skips(corpus_root) -> None:
    plan = _live_plan(corpus_root, "offline", {})  # offline needs no credential
    assert plan.expected_call_count == 6
    assert plan.blocked == []
    assert [f.fixture_id for f in plan.fixtures] == _APPROVED
    assert plan.maximum_call_count == 8
    assert plan.estimated_upper_bound_cost_usd == "0.00156"  # 6 calls
    assert plan.pricing["model_id"] == "gpt-5.4-nano"


def test_live_plan_live_without_credential_blocks_all(corpus_root) -> None:
    plan = _live_plan(corpus_root, "live", {})  # no OPENAI_API_KEY present
    assert plan.expected_call_count == 0
    assert len(plan.blocked) == 6
    for f in plan.blocked:
        assert "missing credential" in f.skip_reason


def test_live_plan_records_destinations_and_caps(corpus_root) -> None:
    plan = _live_plan(corpus_root, "offline", {})
    d = plan.as_dict()
    assert d["fixture_execution_order"] == _APPROVED
    assert d["maximum_call_count"] == 8
    assert all(f["raw_evidence_destination"].endswith("raw") for f in d["fixtures"])
    assert all(f["max_output_tokens"] <= 128 for f in d["fixtures"])
