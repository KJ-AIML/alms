"""Live client construction (offline; no request is made).

Constructing an openai.OpenAI client performs no network I/O. These tests assert the
fail-closed retry/timeout posture without ever calling the provider.
"""

from __future__ import annotations

from probe.client import build_live_client


def test_live_client_disables_sdk_auto_retries():
    client = build_live_client("sk-test-not-a-real-key", 30000)
    assert client.max_retries == 0  # SDK default is 2; audit requires single-attempt


def test_live_client_sets_timeout_from_ms():
    client = build_live_client("sk-test-not-a-real-key", 30000)
    assert client.timeout == 30.0
