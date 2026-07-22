"""Compatibility normalizers — no provider_native fabrication."""

from __future__ import annotations

from typing import Any

from .identity import ENDPOINT_BOUNDARY, build_identity


def normalize_openai_compatible(
    raw: dict[str, Any], *, identity_kwargs: dict[str, Any]
) -> dict[str, Any]:
    response = raw.get("response") or {}
    usage = response.get("usage")
    returned_model = response.get("model")
    identity = build_identity(
        observed_returned_model=returned_model,
        observed_returned_model_source=(
            ENDPOINT_BOUNDARY if returned_model is not None else "unavailable"
        ),
        **identity_kwargs,
    )
    return {
        "evidence_class": "custom_endpoint_compatibility",
        "identity": identity.to_dict(),
        "usage": {
            "raw": usage,
            "source": ENDPOINT_BOUNDARY if usage is not None else "unavailable",
            "provenance": ENDPOINT_BOUNDARY if usage is not None else "unavailable",
        },
        "finish_reason": response.get("choices", [{}])[0].get("finish_reason")
        if response.get("choices")
        else None,
        "tool_calls": _openai_tool_calls(response),
        "disclaimer": (
            "Custom endpoint compatibility evidence is not native-provider evidence. "
            "It does not satisfy G2 or G3."
        ),
    }


def normalize_anthropic_compatible(
    raw: dict[str, Any], *, identity_kwargs: dict[str, Any]
) -> dict[str, Any]:
    response = raw.get("response") or {}
    usage = response.get("usage")
    returned_model = response.get("model")
    identity = build_identity(
        observed_returned_model=returned_model,
        observed_returned_model_source=(
            ENDPOINT_BOUNDARY if returned_model is not None else "unavailable"
        ),
        **identity_kwargs,
    )
    return {
        "evidence_class": "custom_endpoint_compatibility",
        "identity": identity.to_dict(),
        "content_blocks": response.get("content"),
        "stop_reason": response.get("stop_reason"),
        "usage": {
            "raw": usage,
            "source": ENDPOINT_BOUNDARY if usage is not None else "unavailable",
            "provenance": ENDPOINT_BOUNDARY if usage is not None else "unavailable",
        },
        "disclaimer": (
            "Custom endpoint compatibility evidence is not native-provider evidence. "
            "It does not satisfy G2 or G3."
        ),
    }


def _openai_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    choices = response.get("choices") or []
    if not choices:
        return []
    message = choices[0].get("message") or {}
    return list(message.get("tool_calls") or [])
