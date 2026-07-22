"""Secret and URL leakage safety for compatibility evidence."""

from __future__ import annotations

import re
from typing import Any

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
    "base-url",
)

_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)([?&](?:X-Amz-Signature|sig|signature|token|api_key|key)=)[^&\s]+"),
    re.compile(r"(?i)https?://[^\s\"']+"),
)


def _sensitive(key: str) -> bool:
    k = key.lower()
    return any(part in k for part in SENSITIVE_KEY_PARTS)


def redact(obj: Any, secret_values: set[str] | None = None) -> tuple[Any, list[str]]:
    """Return (redacted_copy, sorted redacted field paths)."""
    secrets = {s for s in (secret_values or set()) if s}
    fields: set[str] = set()

    def walk(node: Any, path: str) -> Any:
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


def scan_for_secrets(obj: Any, secret_values: set[str] | None = None) -> list[str]:
    """Return paths that still appear to contain secrets or full URLs."""
    secrets = {s for s in (secret_values or set()) if s}
    hits: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                child = f"{path}/{k}" if path else str(k)
                if _sensitive(str(k)) and isinstance(v, str) and v and v != MASK:
                    hits.append(child)
                walk(v, child)
            return
        if isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
            return
        if isinstance(node, str):
            for secret in secrets:
                if secret and secret in node:
                    hits.append(path or "<root>")
                    return
            if _PATTERNS[0].search(node) or _PATTERNS[1].search(node):
                hits.append(path or "<root>")
                return
            # Full URL leakage (except intentional host-only fields)
            if re.search(r"(?i)https?://", node) and "host" not in (path or "").lower():
                hits.append(path or "<root>")

    walk(obj, "")
    return sorted(set(hits))


def safe_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """Authorization and credential headers are never preserved as values."""
    out: dict[str, str] = {}
    for key, value in (headers or {}).items():
        if _sensitive(key):
            out[key] = MASK
        else:
            out[key] = value
    return out
