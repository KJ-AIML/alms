"""Base URL safety validation for custom endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


class BaseUrlError(ValueError):
    """Invalid or unsafe base URL."""


@dataclass(frozen=True)
class ValidatedBaseUrl:
    """Safe host metadata only — never store the full URL in evidence by default."""

    scheme: str
    host: str
    port: int | None
    path_prefix: str


def validate_base_url(
    base_url: str,
    *,
    allowed_hosts: set[str],
    live_mode: bool,
    allow_localhost_offline: bool = True,
) -> ValidatedBaseUrl:
    """Validate a custom endpoint base URL.

    Live mode requires HTTPS, host allowlist match, no credentials in authority,
    no fragment, and no unexpected query parameters.
    Localhost is permitted only for offline tests when allow_localhost_offline is True.
    """
    if not base_url or not str(base_url).strip():
        raise BaseUrlError("missing base URL")

    parsed = urlparse(base_url.strip())
    if not parsed.scheme:
        raise BaseUrlError("invalid scheme: missing")
    scheme = parsed.scheme.lower()
    if scheme not in ("https", "http"):
        raise BaseUrlError(f"invalid scheme: {scheme}")

    if parsed.username is not None or parsed.password is not None:
        raise BaseUrlError("embedded credentials are forbidden")

    if parsed.fragment:
        raise BaseUrlError("fragment is forbidden")

    if parsed.query:
        raise BaseUrlError("unexpected query parameters are forbidden")

    host = (parsed.hostname or "").lower()
    if not host:
        raise BaseUrlError("missing host")

    localhost = host in {"localhost", "127.0.0.1", "::1"}
    if live_mode:
        if scheme != "https":
            raise BaseUrlError("HTTPS required for live mode")
        if localhost:
            raise BaseUrlError("localhost is not permitted in live mode")
        if host not in {h.lower() for h in allowed_hosts}:
            raise BaseUrlError("host mismatch: not in allowlist")
    else:
        if localhost:
            if not allow_localhost_offline:
                raise BaseUrlError("localhost not permitted")
        elif host not in {h.lower() for h in allowed_hosts} and allowed_hosts:
            raise BaseUrlError("host mismatch: not in allowlist")

    path = parsed.path or ""
    return ValidatedBaseUrl(scheme=scheme, host=host, port=parsed.port, path_prefix=path)


def redirect_host_allowed(original_host: str, location_host: str) -> bool:
    """Redirects that change host are rejected."""
    return original_host.lower() == (location_host or "").lower()
