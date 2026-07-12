"""Offline run orchestration (DevSpec Sections 37, 40).

Dry-run is the default. A live run is refused unless BOTH `--live` and `--confirm-live`
are given AND a valid budget is configured. Live provider execution itself is out of
scope until probes land (P0.4); this slice proves the safety gates and evidence pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import budget as budget_mod
from .config import AuditConfig
from .environment import (
    credential_presence,
    fixture_corpus_hash,
    git_sha,
    os_string,
    python_string,
    sha256_file,
)
from .fixtures import Fixture
from .planner import Plan, build_plan
from .schemas import default_root
from .storage import (
    build_run_manifest,
    now_iso,
    prepare_run_dir,
    write_json_atomic,
    write_run_manifest,
)


class RunError(RuntimeError):
    """Raised to refuse an unsafe or unavailable run."""


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    mode: str  # "dry-run" or "live"
    run_dir: Path
    plan: Plan
    manifest_path: Path


def _plan_dict(plan: Plan) -> dict:
    return {
        "expected_call_count": plan.expected_call_count,
        "planned": [
            {"fixture_id": e.fixture_id, "lane_id": e.lane_id, "will_call": e.will_call}
            for e in plan.planned
        ],
        "skipped": [
            {"fixture_id": e.fixture_id, "lane_id": e.lane_id, "reason": e.skip_reason}
            for e in plan.skipped
        ],
    }


def run(
    *,
    run_id: str,
    fixtures: list[Fixture],
    lanes: list[dict],
    config: AuditConfig,
    live: bool = False,
    confirm_live: bool = False,
    model_configuration: dict | None = None,
    command_line: str = "",
    root: Path | None = None,
) -> RunSummary:
    root = root or default_root()
    providers = sorted({ln.get("provider", "?") for ln in lanes})
    creds = credential_presence(providers)
    plan = build_plan(fixtures, lanes, live=live, credentials=creds)

    # Preflight safety gates (DevSpec Section 40).
    if live:
        if not confirm_live:
            raise RunError("live run refused: --confirm-live is required alongside --live")
        budget_mod.check_live_budget(config)  # fails closed when no budget
        budget_mod.check_call_cap(plan.expected_call_count, config)
        raise RunError(
            "live run gates passed, but no runtime probes exist yet (arriving in P0.4). "
            "Re-run without --live for a dry-run, or wait for the probe slices."
        )

    mode = "dry-run"
    started = now_iso()
    run_dir = prepare_run_dir(run_id, root)  # raises if not writable

    harness_lock = root / "harness" / "uv.lock"
    manifest = build_run_manifest(
        run_id=run_id,
        git_sha=git_sha(root.parents[1]) if len(root.parents) >= 2 else "unknown",
        harness_lock_hash=sha256_file(harness_lock) if harness_lock.is_file() else "absent",
        probe_lock_hashes={},
        fixture_corpus_hash=fixture_corpus_hash([f.path for f in fixtures])
        if fixtures
        else "empty",
        os_string=os_string(),
        python=python_string(),
        selected_lanes=[ln.get("lane_id", "?") for ln in lanes],
        selected_fixtures=[f.id for f in fixtures],
        model_configuration=model_configuration or {},
        credential_presence=creds,
        hard_cap_usd=config.hard_cap_usd,
        max_calls=config.max_live_calls,
        command_line=command_line,
        started_at=started,
        ended_at=now_iso(),
    )
    manifest_path = write_run_manifest(run_dir, manifest, root)
    write_json_atomic(run_dir / "plan.json", _plan_dict(plan))
    return RunSummary(
        run_id=run_id, mode=mode, run_dir=run_dir, plan=plan, manifest_path=manifest_path
    )
