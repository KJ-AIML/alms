"""Narrow secret redaction for raw OpenAI artifacts (DevSpec Section 85).

Local to the probe (probes are isolated and must not import the harness). Masks API
keys, Authorization/Bearer, cookies, and signed-URL signatures; preserves benign
evidence such as request IDs, model IDs, usage, and synthetic content.
"""

from __future__ import annotations

import re

MASK = "<redacted>"

SENSITIVE_KEY_PARTS = (
    "authorization",
    "api_key",
    "api-key",
    "apikey",
    "x-api-key",
    "cookie",
    "set-cookie",
    "token",
    "secret",
    "password",
    "bearer",
    "signature",
)

_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)([?&](?:X-Amz-Signature|sig|signature|token|api_key|key)=)[^&\s]+"),
)


def _sensitive(key: str) -> bool:
    k = key.lower()
    return any(part in k for part in SENSITIVE_KEY_PARTS)


def _redact_str(value: str, secret_values: set[str]) -> tuple[str, bool]:
    out = value
    for secret in secret_values:
        if secret and secret in out:
            out = out.replace(secret, MASK)
    out = _PATTERNS[0].sub("Bearer " + MASK, out)
    out = _PATTERNS[1].sub(MASK, out)
    out = _PATTERNS[2].sub(r"\1" + MASK, out)
    return out, out != value


def redact(obj, secret_values: set[str] | None = None) -> tuple[object, list[str]]:
    """Return (redacted_copy, sorted list of redacted field paths)."""
    secrets = {s for s in (secret_values or set()) if s}
    fields: set[str] = set()

    def walk(node, path: str):
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                child = f"{path}/{k}" if path else str(k)
                if isinstance(v, str) and _sensitive(str(k)):
                    out[k] = MASK
                    fields.add(child)
                else:
                    out[k] = walk(v, child)
            return out
        if isinstance(node, list):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(node)]
        if isinstance(node, str):
            new, changed = _redact_str(node, secrets)
            if changed:
                fields.add(path or "<root>")
            return new
        return node

    return walk(obj, ""), sorted(fields)
