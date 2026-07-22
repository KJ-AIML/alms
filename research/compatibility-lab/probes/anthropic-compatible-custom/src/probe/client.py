"""Anthropic SDK client construction for custom endpoints."""

from __future__ import annotations

from typing import Any

import httpx


def build_offline_client(
    *,
    transport: httpx.BaseTransport,
    base_url: str,
    api_key: str = "offline-mock-key",
    timeout_ms: int = 30000,
) -> Any:
    import anthropic

    http_client = httpx.Client(
        transport=transport,
        timeout=max(timeout_ms, 1) / 1000.0,
        follow_redirects=False,
    )
    return anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
        http_client=http_client,
        max_retries=0,
        timeout=max(timeout_ms, 1) / 1000.0,
    )


def build_live_client(*, api_key: str, base_url: str, timeout_ms: int = 30000) -> Any:
    import anthropic

    return anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
        max_retries=0,
        timeout=max(timeout_ms, 1) / 1000.0,
    )


def client_retry_config(client: Any) -> dict[str, Any]:
    return {
        "anthropic_client_max_retries": getattr(client, "max_retries", None),
        "probe_retry": "none",
    }


def supports_custom_base_url() -> dict[str, Any]:
    """Preflight: installed SDK supports base_url on Anthropic()."""
    import anthropic
    import inspect

    sig = inspect.signature(anthropic.Anthropic.__init__)
    params = set(sig.parameters)
    supported = "base_url" in params
    return {
        "sdk": "anthropic",
        "version": getattr(anthropic, "__version__", None),
        "base_url_param_present": supported,
        "status": "SUPPORTED" if supported else "UNSUPPORTED",
        "reason": None
        if supported
        else "installed SDK surface does not provide a safe supported configuration path",
    }
