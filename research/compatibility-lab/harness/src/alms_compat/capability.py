"""Capability fingerprinting for custom endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CapabilityState = Literal[
    "declared",
    "observed_offline",
    "observed_live",
    "unsupported",
    "inconclusive",
    "not_tested",
]

DIMENSIONS: tuple[str, ...] = (
    "text_generation",
    "system_or_developer_roles",
    "structured_output",
    "tool_definitions",
    "tool_calls",
    "streaming",
    "usage_reporting",
    "cache_usage",
    "reasoning_metadata",
    "model_identity",
    "error_taxonomy",
    "request_cancellation",
    "timeout_ownership",
)


@dataclass
class CapabilityProfile:
    lane_id: str
    api_family: str
    sdk_family: str
    boundary_kind: str
    evidence_class: str = "custom_endpoint_compatibility"
    capabilities: dict[str, CapabilityState] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "api_family": self.api_family,
            "sdk_family": self.sdk_family,
            "boundary_kind": self.boundary_kind,
            "evidence_class": self.evidence_class,
            "disclaimer": (
                "Custom endpoint compatibility evidence is not native-provider evidence. "
                "It does not satisfy G2 or G3."
            ),
            "capabilities": dict(self.capabilities),
            "notes": dict(self.notes),
        }


def empty_profile(
    lane_id: str, api_family: str, sdk_family: str, boundary_kind: str
) -> CapabilityProfile:
    return CapabilityProfile(
        lane_id=lane_id,
        api_family=api_family,
        sdk_family=sdk_family,
        boundary_kind=boundary_kind,
        capabilities={dim: "not_tested" for dim in DIMENSIONS},
    )


def set_capability(
    profile: CapabilityProfile,
    dimension: str,
    state: CapabilityState,
    note: str | None = None,
) -> None:
    if dimension not in DIMENSIONS:
        raise ValueError(f"unknown capability dimension: {dimension}")
    profile.capabilities[dimension] = state
    if note:
        profile.notes[dimension] = note
