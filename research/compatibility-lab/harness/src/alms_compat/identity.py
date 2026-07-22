"""Endpoint, gateway, SDK, and model identity without conflation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# Additive ownership label for compatibility artifacts only.
# Not a mutation of the central nine-term provenance vocabulary.
ENDPOINT_BOUNDARY = "endpoint_boundary"

PROVENANCE_DECISION = "B"  # additive endpoint-boundary field is sufficient


@dataclass(frozen=True)
class EndpointIdentity:
    endpoint_id: str
    endpoint_family: str
    boundary_kind: str
    sdk_family: str
    configured_provider_claim: str | None
    configured_gateway_claim: str | None
    requested_model: str
    observed_returned_model: str | None
    observed_returned_model_source: str
    model_identity_match: bool | None
    raw_model_reference: str | None
    execution_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_identity(
    *,
    endpoint_id: str,
    endpoint_family: str,
    boundary_kind: str,
    sdk_family: str,
    provider_claim: str | None,
    gateway_claim: str | None,
    requested_model: str,
    observed_returned_model: str | None,
    observed_returned_model_source: str,
    execution_mode: str,
    raw_model_reference: str | None = None,
) -> EndpointIdentity:
    """Build identity without inventing provider or returned-model values."""
    if observed_returned_model is None:
        match: bool | None = None
        source = observed_returned_model_source or "unavailable"
    else:
        match = observed_returned_model == requested_model
        source = observed_returned_model_source
    return EndpointIdentity(
        endpoint_id=endpoint_id,
        endpoint_family=endpoint_family,
        boundary_kind=boundary_kind,
        sdk_family=sdk_family,
        configured_provider_claim=provider_claim,
        configured_gateway_claim=gateway_claim,
        requested_model=requested_model,
        observed_returned_model=observed_returned_model,
        observed_returned_model_source=source,
        model_identity_match=match,
        raw_model_reference=raw_model_reference
        if raw_model_reference is not None
        else observed_returned_model,
        execution_mode=execution_mode,
    )


def provider_claim_is_not_identity(identity: EndpointIdentity) -> bool:
    """Gateway/provider claims are claims, not verified identities."""
    return True


def forbid_provider_native_for_custom(execution_mode: str, provenance_term: str) -> bool:
    """Custom-endpoint modes must not fabricate provider_native provenance."""
    if provenance_term != "provider_native":
        return True
    return execution_mode not in {"offline_mock", "live_custom_endpoint", "offline_sdk_transport"}
