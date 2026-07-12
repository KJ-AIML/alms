"""Matrix planner (DevSpec Sections 39 and 45).

Builds the fixture x lane matrix and explains every skip. A missing result with no
explanation is a harness failure, so each skipped pair carries a reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .environment import provider_env_var
from .fixtures import Fixture


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
