"""Matrix planner (DevSpec Sections 39 and 45).

Builds the fixture x lane matrix and explains every skip. A missing result with no
explanation is a harness failure, so each skipped pair carries a reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import AuditConfig
from .environment import provider_env_var
from .fixtures import Fixture
from .pricing import PricingSnapshot, upper_bound_cost


@dataclass(frozen=True)
class PlanEntry:
    fixture_id: str
    lane_id: str
    provider: str
    will_call: bool  # would consume a live provider call
    skip_reason: str | None  # None means planned


@dataclass
class Plan:
    entries: list[PlanEntry] = field(default_factory=list)

    @property
    def planned(self) -> list[PlanEntry]:
        return [e for e in self.entries if e.skip_reason is None]

    @property
    def skipped(self) -> list[PlanEntry]:
        return [e for e in self.entries if e.skip_reason is not None]

    @property
    def expected_call_count(self) -> int:
        return sum(1 for e in self.planned if e.will_call)


def build_plan(
    fixtures: list[Fixture],
    lanes: list[dict],
    *,
    live: bool,
    credentials: dict[str, bool] | None = None,
) -> Plan:
    """Deterministic fixture x lane matrix.

    In dry-run (`live=False`) nothing is skipped for missing credentials — planning is
    always previewable without secrets. In a live plan, a live-required fixture on a lane
    whose provider credential is absent is skipped WITH a reason.
    """
    credentials = credentials or {}
    plan = Plan()
    for fx in sorted(fixtures, key=lambda f: f.id):
        reqs = fx.data.get("requirements", {})
        live_required = bool(reqs.get("live_required"))
        for lane in sorted(lanes, key=lambda ln: ln.get("lane_id", "")):
            lane_id = lane.get("lane_id", "?")
            provider = lane.get("provider", "?")
            skip: str | None = None
            if live and live_required:
                env_var = provider_env_var(provider)
                if not credentials.get(env_var, False):
                    skip = f"missing credential {env_var} for provider {provider}"
            plan.entries.append(
                PlanEntry(
                    fixture_id=fx.id,
                    lane_id=lane_id,
                    provider=provider,
                    will_call=live_required,
                    skip_reason=skip,
                )
            )
    return plan


# --- Bounded single-lane live/offline execution plan (DevSpec Sections 39 and 45) ---


@dataclass(frozen=True)
class LiveFixturePlan:
    fixture_id: str
    will_call: bool
    skip_reason: str | None
    max_output_tokens: int
    timeout_ms: int
    stream: bool
    output_dir: str
    raw_dir: str
    normalized_path: str
    result_path: str


@dataclass(frozen=True)
class LivePlan:
    mode: str  # "offline" | "live"
    lane: dict
    model: str
    fixtures: list[LiveFixturePlan]
    maximum_call_count: int
    hard_cap_usd: float | None
    soft_cap_usd: float | None
    default_timeout_ms: int
    retries: int
    credential_presence: dict[str, bool]
    probe_project_dir: str
    probe_run_command: list[str]
    pricing: dict | None
    estimated_upper_bound_cost_usd: str | None

    @property
    def expected_call_count(self) -> int:
        # The single source of truth for the call count (never maintained separately).
        return sum(1 for f in self.fixtures if f.will_call and f.skip_reason is None)

    @property
    def blocked(self) -> list[LiveFixturePlan]:
        return [f for f in self.fixtures if f.skip_reason is not None]

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "lane_id": self.lane.get("lane_id"),
            "lane": self.lane,
            "model": self.model,
            "fixture_execution_order": [f.fixture_id for f in self.fixtures],
            "expected_call_count": self.expected_call_count,
            "maximum_call_count": self.maximum_call_count,
            "default_timeout_ms": self.default_timeout_ms,
            "retries": self.retries,
            "hard_cap_usd": self.hard_cap_usd,
            "soft_cap_usd": self.soft_cap_usd,
            "pricing_snapshot": self.pricing,
            "estimated_upper_bound_cost_usd": self.estimated_upper_bound_cost_usd,
            "credential_presence": self.credential_presence,
            "probe_project_dir": self.probe_project_dir,
            "probe_run_command": self.probe_run_command,
            "fixtures": [
                {
                    "fixture_id": f.fixture_id,
                    "will_call": f.will_call,
                    "skip_reason": f.skip_reason,
                    "max_output_tokens": f.max_output_tokens,
                    "timeout_ms": f.timeout_ms,
                    "stream": f.stream,
                    "raw_evidence_destination": f.raw_dir,
                    "normalized_evidence_destination": f.normalized_path,
                    "result_destination": f.result_path,
                }
                for f in self.fixtures
            ],
            "blocked_fixtures": [
                {"fixture_id": f.fixture_id, "skip_reason": f.skip_reason} for f in self.blocked
            ],
        }


def build_live_plan(
    *,
    mode: str,
    lane: dict,
    model: str,
    fixtures: list[Fixture],
    config: AuditConfig,
    credentials: dict[str, bool],
    run_dir: Path,
    probe_project_dir: Path,
    probe_run_command: list[str],
    pricing: PricingSnapshot | None,
) -> LivePlan:
    """Derive the exact bounded execution matrix for one lane + explicit model.

    `mode` "live" skips a live-required fixture whose provider credential is absent (fail
    closed with a reason). `mode` "offline" runs the probe mock and never needs a credential.
    Fixture order is exactly the selection order.
    """
    provider = lane.get("provider", "?")
    env_var = provider_env_var(provider)
    cred_present = credentials.get(env_var, False)

    fx_plans: list[LiveFixturePlan] = []
    for fx in fixtures:
        execution = fx.data.get("execution", {})
        live_required = fx.live_required
        skip: str | None = None
        if mode == "live" and live_required and not cred_present:
            skip = f"missing credential {env_var} for provider {provider}"
        out_dir = run_dir / "fixtures" / fx.id
        fx_plans.append(
            LiveFixturePlan(
                fixture_id=fx.id,
                will_call=live_required,
                skip_reason=skip,
                max_output_tokens=min(
                    int(execution.get("max_output_tokens", config.max_output_tokens)),
                    config.max_output_tokens,
                ),
                timeout_ms=int(execution.get("timeout_ms", config.default_timeout_ms)),
                stream=bool(execution.get("stream")),
                output_dir=str(out_dir),
                raw_dir=str(out_dir / "raw"),
                normalized_path=str(out_dir / "normalized-transcript.json"),
                result_path=str(out_dir / "result.json"),
            )
        )

    expected = sum(1 for f in fx_plans if f.will_call and f.skip_reason is None)
    estimate: str | None = None
    if pricing is not None:
        estimate = str(upper_bound_cost(pricing, expected))

    return LivePlan(
        mode=mode,
        lane=lane,
        model=model,
        fixtures=fx_plans,
        maximum_call_count=config.max_live_calls,
        hard_cap_usd=config.hard_cap_usd,
        soft_cap_usd=config.soft_cap_usd,
        default_timeout_ms=config.default_timeout_ms,
        retries=config.retries,
        credential_presence={env_var: cred_present},
        probe_project_dir=str(probe_project_dir),
        probe_run_command=probe_run_command,
        pricing=pricing.as_evidence() if pricing else None,
        estimated_upper_bound_cost_usd=estimate,
    )
