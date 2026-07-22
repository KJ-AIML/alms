"""OpenAI SDK client construction for custom endpoints."""

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
    """Real OpenAI client with custom base_url and zero retries over a mock transport."""
    import openai

    http_client = httpx.Client(
        transport=transport,
        timeout=max(timeout_ms, 1) / 1000.0,
        follow_redirects=False,
    )
    return openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=http_client,
        max_retries=0,
        timeout=max(timeout_ms, 1) / 1000.0,
    )


def build_live_client(
    *,
    api_key: str,
    base_url: str,
    timeout_ms: int = 30000,
) -> Any:
    """Live custom-endpoint client. Retries forced to zero."""
    import openai

    return openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
        max_retries=0,
        timeout=max(timeout_ms, 1) / 1000.0,
    )


def client_retry_config(client: Any) -> dict[str, Any]:
    return {
        "openai_client_max_retries": getattr(client, "max_retries", None),
        "probe_retry": "none",
    }
