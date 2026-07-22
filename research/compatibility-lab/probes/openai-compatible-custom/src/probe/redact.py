"""Local secret redaction (probe-isolated)."""

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
    "base_url",
)

_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)([?&](?:X-Amz-Signature|sig|signature|token|api_key|key)=)[^&\s]+"),
)


def _sensitive(key: str) -> bool:
    k = key.lower()
    return any(part in k for part in SENSITIVE_KEY_PARTS)


def redact(obj, secret_values: set[str] | None = None) -> tuple[object, list[str]]:
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
            new = node
            for secret in secrets:
                if secret and secret in new:
                    new = new.replace(secret, MASK)
            new = _PATTERNS[0].sub("Bearer " + MASK, new)
            new = _PATTERNS[1].sub(MASK, new)
            new = _PATTERNS[2].sub(r"\1" + MASK, new)
            if new != node:
                fields.add(path or "<root>")
            return new
        return node

    return walk(obj, ""), sorted(fields)


def safe_headers(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in headers.items():
        if _sensitive(key):
            out[key] = MASK
        else:
            out[key] = value
    return out
