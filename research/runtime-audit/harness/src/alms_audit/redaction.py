"""Raw-artifact redaction (DevSpec Section 85).

Removes/masks API keys, authorization headers, bearer tokens, cookies, signed-URL
signatures, secret query params, and any configured secret values. Preserves benign
evidence (request IDs, timestamps, model IDs, usage, status codes, synthetic content).
"""

from __future__ import annotations

import re

MASK = "<redacted>"

# Dict keys whose VALUE is always secret (compared case-insensitively, substring match).
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
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
    re.compile(r"(?i)([?&](?:X-Amz-Signature|sig|signature|token|api_key|key)=)[^&\s]+"),
)


def _sensitive_key(key: str) -> bool:
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
    """Return (redacted_copy, sorted_list_of_redacted_field_paths)."""
    secret_values = {s for s in (secret_values or set()) if s}
    redacted_fields: set[str] = set()

    def walk(node, path: str):
        if isinstance(node, dict):
            result = {}
            for k, v in node.items():
                child_path = f"{path}/{k}" if path else k
                if isinstance(v, str) and _sensitive_key(str(k)):
                    result[k] = MASK
                    redacted_fields.add(child_path)
                else:
                    result[k] = walk(v, child_path)
            return result
        if isinstance(node, list):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(node)]
        if isinstance(node, str):
            new, changed = _redact_str(node, secret_values)
            if changed:
                redacted_fields.add(path or "<root>")
            return new
        return node

    return walk(obj, ""), sorted(redacted_fields)
