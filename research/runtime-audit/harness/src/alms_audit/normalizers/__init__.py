"""Runtime-specific normalizers.

A normalizer converts serialized raw evidence (plain JSON, never SDK objects) into the
candidate audit vocabulary (DevSpec Section 43). Normalizers live in the harness and must
NOT import any provider or framework SDK; they read only the raw JSON a probe wrote. They
preserve raw references and emit provider_extension / framework_extension events for
semantics that do not fit the vocabulary.

Each normalizer module exposes a uniform interface:
  * extract_usage(capture_kind, raw_obj) -> dict | None
  * normalize(capture_kind, raw_obj, raw_manifest, response_ref) -> transcript dict
`select(runtime_layer)` returns the module for a lane's runtime layer.
"""

from __future__ import annotations


def select(runtime_layer: str | None):
    """Return the normalizer module for a lane's runtime layer (default: openai)."""
    from . import anthropic, gemini, langchain, openai

    return {
        "openai": openai,
        "langchain": langchain,
        "anthropic": anthropic,
        "google-genai": gemini,
    }.get(runtime_layer or "", openai)
