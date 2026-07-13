"""Isolation and safety: the offline model boundary and the no-telemetry / no-Gateway guarantees.

PydanticAI is importable HERE (the probe env) but ALLOW_MODEL_REQUESTS is False, no real provider
model can be built, full Logfire and the OpenTelemetry SDK/exporter are absent, no Gateway client
is constructed, and no credential is required offline.
"""

from __future__ import annotations

import importlib.util

from conftest import run_fixture
from probe import client


def test_pydantic_ai_importable_in_probe():
    import pydantic_ai  # noqa: F401
    import pydantic_ai.models.function  # noqa: F401


def test_allow_model_requests_is_false_after_isolation():
    import pydantic_ai.models as models

    client.configure_pydanticai_isolation()
    assert models.ALLOW_MODEL_REQUESTS is False


def test_function_model_is_the_primary_seam():
    caps = client.offline_capabilities()
    assert caps["primary_model_seam"] == "FunctionModel"
    assert caps["test_model_excluded_as_primary"] is True
    assert caps["allow_model_requests"] is False


def test_no_real_provider_model_constructible():
    intro = client.isolation_introspection()
    # openai/anthropic/google integrations need vendor SDKs absent in this slim install.
    assert intro["openai_provider_integration_importable"] is False
    assert intro["openai_provider_integration_error"] is not None


def test_full_logfire_and_otel_sdk_absent():
    intro = client.isolation_introspection()
    assert intro["logfire_full_installed"] is False
    assert intro["opentelemetry_sdk_installed"] is False
    # The inert interface shims may be present transitively; that is not an exporter.
    assert importlib.util.find_spec("logfire") is None
    assert importlib.util.find_spec("opentelemetry.sdk") is None


def test_instrumentation_and_gateway_off():
    intro = client.isolation_introspection()
    assert intro["agent_instrument_default"] is False
    assert intro["gateway_client_used"] is False
    assert intro["custom_endpoint_configured"] is False
    assert intro["router_or_fallback_used"] is False


def test_offline_run_requires_no_credential(monkeypatch):
    # Nothing reads a provider key on the offline path; a run succeeds with the env cleared.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    capture, _op, _scenario = run_fixture("GEN-001")
    assert capture.kind == "response"
    assert capture.invocations == 1


def test_no_secret_value_in_capture():
    # A synthetic credential-shaped value must never appear in captured evidence (none is used).
    capture, _op, _scenario = run_fixture("GEN-001")
    blob = repr(capture)
    assert "sk-" not in blob
    assert "Bearer " not in blob
