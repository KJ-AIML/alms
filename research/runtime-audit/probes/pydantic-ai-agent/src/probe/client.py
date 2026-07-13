"""PydanticAI isolation, offline model boundary, and framework introspection.

This lane audits the PydanticAI Agent, NOT the Pydantic AI Gateway. Every automatic behavior
that could add a hidden call, mutate evidence, or exfiltrate a prompt is disabled or proven
absent: real provider requests are gated off (ALLOW_MODEL_REQUESTS=False), instrumentation is
never enabled, Logfire and the OpenTelemetry SDK/exporter are not installed, no Gateway client
is constructed, and every retry budget is zero. No Router / fallback / custom endpoint exists.

The offline model is FunctionModel — PydanticAI's OWN explicit-control seam. It still runs the
real Agent graph, the real message/part model, real output-strategy selection (NativeOutput),
real validation, real deferred-tool handling, real usage aggregation, and real stream events, so
this is not a harness-prebuilt response and not a normalized transcript. What it does NOT exercise
is any real provider request/response semantics, which stay unverified_until_live.
"""

from __future__ import annotations

import importlib.util
from typing import Any

import pydantic_ai.models as pai_models
from pydantic_ai import AgentRetries
from pydantic_ai.profiles import ModelProfile
from pydantic_ai.usage import UsageLimits

# PydanticAI's Agent output (messages, parts, usage aggregation, terminal states, model_name) is
# FRAMEWORK-owned. Under a LIVE call the observed returned model exposed through PydanticAI objects
# is framework_native, NEVER provider_native (a real provider-native model id would require direct
# provider evidence). Offline evidence is downgraded to fixture_expected by the shared result
# builder. Exposed for the harness manifest.
MODEL_IDENTITY_LIVE_SOURCE = "framework_native"

# The offline FunctionModel's synthetic identity. It is deliberately DISTINCT from any requested
# provider model, so requested != observed is recorded (model_identity_match=false), non-failing,
# with source fixture_expected. The requested model is never copied into the observed field.
SYNTHETIC_MODEL_NAME = "function:offline-synthetic-model"

# Zero retries across every framework owner PydanticAI exposes. `output` = output-validation
# retries; `tools` = tool-execution retries. Set explicitly to 0 (not left to the default), and
# measured by FunctionModel invocation count, never inferred from configuration alone.
AGENT_RETRIES: AgentRetries = AgentRetries(output=0, tools=0)
TOOL_RETRIES = 0  # per-tool retry budget (also zero)

# One model request per fixture. UsageLimits(request_limit=1) makes a second model turn a hard
# UsageLimitExceeded rather than a silent extra call.
REQUEST_LIMIT = 1


def usage_limits() -> UsageLimits:
    return UsageLimits(request_limit=REQUEST_LIMIT)


def configure_pydanticai_isolation() -> dict:
    """Gate real provider requests and return the effective isolation state as evidence.

    Never assumes a value is safe by default: it forces ALLOW_MODEL_REQUESTS=False (default is
    True) and records the concrete instrumentation/Gateway/exporter facts so the manifest shows
    what was actually in force. FunctionModel is exempt from the ALLOW_MODEL_REQUESTS gate (it is
    a test model), so the offline lane still runs while every real provider model is blocked.
    """
    pai_models.ALLOW_MODEL_REQUESTS = False
    return isolation_introspection()


def _provider_integration_available() -> dict:
    """Prove a real PydanticAI provider integration cannot be constructed in this slim env.

    The `logfire-api` and `opentelemetry-api` packages are present as transitive PydanticAI
    dependencies, but they are inert interface shims: full `logfire` and the OpenTelemetry SDK /
    exporter are NOT installed, so no telemetry can leave the process. Provider model integrations
    (openai/anthropic/google) require their vendor SDKs, which are absent in this slim install, so
    `import pydantic_ai.models.openai` fails. This distinguishes 'a shim package exists' from 'a
    real provider/exporter is reachable'.
    """
    try:
        importlib.import_module("pydantic_ai.models.openai")
        openai_integration = True
        openai_error = None
    except Exception as exc:  # noqa: BLE001 - the import failure IS the evidence
        openai_integration = False
        openai_error = f"{type(exc).__name__}: {exc}"
    return {
        "openai_provider_integration_importable": openai_integration,
        "openai_provider_integration_error": openai_error,
    }


def isolation_introspection() -> dict:
    """Record the ALLOW_MODEL_REQUESTS gate, instrumentation, exporter, and retry ownership."""
    from pydantic_ai import Agent

    return {
        "allow_model_requests": bool(getattr(pai_models, "ALLOW_MODEL_REQUESTS", True)),
        # Instrumentation is never enabled: instrument_all() is not called and no Instrumentation
        # settings are passed. The global default is read back as evidence, not assumed.
        "agent_instrument_default": getattr(Agent, "_instrument_default", None) is not None
        and bool(getattr(Agent, "_instrument_default")),
        "logfire_full_installed": importlib.util.find_spec("logfire") is not None,
        "logfire_api_shim_installed": importlib.util.find_spec("logfire_api") is not None,
        "opentelemetry_sdk_installed": importlib.util.find_spec("opentelemetry.sdk") is not None,
        "opentelemetry_api_installed": importlib.util.find_spec("opentelemetry") is not None,
        "gateway_client_used": False,  # no Pydantic AI Gateway client is ever constructed
        "custom_endpoint_configured": False,  # no base_url / custom provider endpoint
        "router_or_fallback_used": False,  # no FallbackModel / router
        "retry_budgets": {
            "output_validation_retries": AGENT_RETRIES.get("output"),
            "tool_retries": AGENT_RETRIES.get("tools"),
            "per_tool_retries": TOOL_RETRIES,
            "request_limit": REQUEST_LIMIT,
        },
        **_provider_integration_available(),
    }


def native_output_profile() -> tuple[ModelProfile, dict]:
    """Build the SYNTHETIC model profile that advertises native structured-output support.

    `NativeOutput` is grounded in a model profile's `supports_json_schema_output` capability. We
    supply that capability EXPLICITLY here as synthetic offline configuration — it is NOT inferred
    from any real provider. Declaring it explicitly (rather than relying on FunctionModel's
    permissive default) is what keeps the evidence honest: the flag is the probe's own, labelled
    synthetic. The returned record is preserved in raw evidence so a test can prove the capability
    was declared by the probe, not observed from a live provider.
    """
    profile = ModelProfile(supports_json_schema_output=True)
    record = {
        "supports_json_schema_output": True,
        "source": "synthetic_offline_configuration",
        "inferred_from_real_provider": False,
        "note": (
            "Synthetic capability flag set by the probe so PydanticAI selects NativeOutput "
            "offline. It proves the framework's native-output request path (schema generation + "
            "ModelRequestParameters preparation + FunctionModel receipt + parse/validate), NOT "
            "that any real provider supports or follows native JSON-schema output "
            "(unverified_until_live)."
        ),
    }
    return profile, record


def offline_capabilities() -> dict[str, Any]:
    """A compact capability snapshot for the manifest / README verification."""
    return {
        "primary_model_seam": "FunctionModel",
        "test_model_excluded_as_primary": True,
        "allow_model_requests": False,
        "model_identity_live_source": MODEL_IDENTITY_LIVE_SOURCE,
        "synthetic_offline_model_name": SYNTHETIC_MODEL_NAME,
    }
