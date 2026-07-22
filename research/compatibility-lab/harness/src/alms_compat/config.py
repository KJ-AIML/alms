"""Typed custom-endpoint configuration contract."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .urls import BaseUrlError, ValidatedBaseUrl, validate_base_url


class ApiFamily(str, Enum):
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC_COMPATIBLE = "anthropic_compatible"


class SdkFamily(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class BoundaryKind(str, Enum):
    CUSTOM_ENDPOINT = "custom_endpoint"
    GATEWAY = "gateway"
    PROXY = "proxy"
    UNKNOWN = "unknown"


class ConfigError(ValueError):
    """Invalid or incomplete endpoint configuration."""


@dataclass(frozen=True)
class EndpointConfig:
    """Safe configuration surface for a custom endpoint lane.

    `base_url` and credential values remain environment-only and are not written to evidence
    by default. Outside probe children, only `credential_present` is recorded.
    """

    endpoint_id: str
    api_family: ApiFamily
    sdk_family: SdkFamily
    boundary_kind: BoundaryKind
    model: str
    provider_claim: str | None
    gateway_claim: str | None
    live_confirmed: bool
    allowed_hosts: frozenset[str]
    credential_present: bool
    validated_base_url: ValidatedBaseUrl | None
    hard_call_cap: int
    max_output_tokens: int

    def evidence_identity(self) -> dict[str, str]:
        """Fields safe to persist in evidence artifacts."""
        return {
            "endpoint_id": self.endpoint_id,
            "api_family": self.api_family.value,
            "boundary_kind": self.boundary_kind.value,
            "sdk_family": self.sdk_family.value,
        }


_OPENAI_ENV = {
    "base_url": "ALMS_COMPAT_OPENAI_BASE_URL",
    "api_key": "ALMS_COMPAT_OPENAI_API_KEY",
    "model": "ALMS_COMPAT_OPENAI_MODEL",
    "endpoint_id": "ALMS_COMPAT_OPENAI_ENDPOINT_ID",
    "provider_claim": "ALMS_COMPAT_OPENAI_PROVIDER_CLAIM",
    "gateway_claim": "ALMS_COMPAT_OPENAI_GATEWAY_CLAIM",
    "boundary_kind": "ALMS_COMPAT_OPENAI_BOUNDARY_KIND",
}

_ANTHROPIC_ENV = {
    "base_url": "ALMS_COMPAT_ANTHROPIC_BASE_URL",
    "api_key": "ALMS_COMPAT_ANTHROPIC_API_KEY",
    "model": "ALMS_COMPAT_ANTHROPIC_MODEL",
    "endpoint_id": "ALMS_COMPAT_ANTHROPIC_ENDPOINT_ID",
    "provider_claim": "ALMS_COMPAT_ANTHROPIC_PROVIDER_CLAIM",
    "gateway_claim": "ALMS_COMPAT_ANTHROPIC_GATEWAY_CLAIM",
    "boundary_kind": "ALMS_COMPAT_ANTHROPIC_BOUNDARY_KIND",
}


def _parse_hosts(raw: str | None) -> frozenset[str]:
    if not raw or not raw.strip():
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def _parse_boundary(raw: str | None) -> BoundaryKind:
    if not raw:
        return BoundaryKind.UNKNOWN
    try:
        return BoundaryKind(raw.strip().lower())
    except ValueError as exc:
        raise ConfigError(f"invalid boundary_kind: {raw}") from exc


def load_endpoint_config(
    api_family: ApiFamily,
    *,
    env: Mapping[str, str] | None = None,
    require_live: bool = False,
    include_base_url: bool = True,
) -> EndpointConfig:
    """Load endpoint configuration from environment variables.

    Credential values are read only to compute `credential_present` and are never returned.
    """
    environ = env if env is not None else os.environ
    mapping = _OPENAI_ENV if api_family is ApiFamily.OPENAI_COMPATIBLE else _ANTHROPIC_ENV
    sdk = SdkFamily.OPENAI if api_family is ApiFamily.OPENAI_COMPATIBLE else SdkFamily.ANTHROPIC

    endpoint_id = (environ.get(mapping["endpoint_id"]) or "").strip()
    if not endpoint_id:
        raise ConfigError("missing endpoint ID")

    model = (environ.get(mapping["model"]) or "").strip()
    if not model:
        raise ConfigError("missing model")

    credential_present = bool((environ.get(mapping["api_key"]) or "").strip())
    live_confirmed = (environ.get("ALMS_COMPAT_CONFIRM_LIVE") or "").strip() == "1"
    allowed_hosts = _parse_hosts(environ.get("ALMS_COMPAT_ALLOWED_HOSTS"))

    if require_live and not live_confirmed:
        raise ConfigError("live confirm absent")
    if require_live and not credential_present:
        raise ConfigError("credential absent")
    if require_live and not allowed_hosts:
        raise ConfigError("missing host allowlist")

    base_raw = (environ.get(mapping["base_url"]) or "").strip()
    validated: ValidatedBaseUrl | None = None
    if include_base_url:
        if not base_raw:
            if require_live:
                raise ConfigError("missing base URL")
        else:
            try:
                validated = validate_base_url(
                    base_raw,
                    allowed_hosts=set(allowed_hosts),
                    live_mode=require_live or live_confirmed,
                    allow_localhost_offline=not (require_live or live_confirmed),
                )
            except BaseUrlError as exc:
                raise ConfigError(str(exc)) from exc

    hard_cap = int((environ.get("ALMS_COMPAT_HARD_CALL_CAP") or "6").strip())
    max_tokens = int((environ.get("ALMS_COMPAT_MAX_OUTPUT_TOKENS") or "256").strip())

    return EndpointConfig(
        endpoint_id=endpoint_id,
        api_family=api_family,
        sdk_family=sdk,
        boundary_kind=_parse_boundary(environ.get(mapping["boundary_kind"])),
        model=model,
        provider_claim=(environ.get(mapping["provider_claim"]) or None),
        gateway_claim=(environ.get(mapping["gateway_claim"]) or None),
        live_confirmed=live_confirmed,
        allowed_hosts=allowed_hosts,
        credential_present=credential_present,
        validated_base_url=validated if include_base_url else None,
        hard_call_cap=hard_cap,
        max_output_tokens=max_tokens,
    )


def live_preflight(
    api_family: ApiFamily, *, env: Mapping[str, str] | None = None
) -> EndpointConfig:
    """Fail-closed live activation preflight."""
    return load_endpoint_config(api_family, env=env, require_live=True, include_base_url=True)
