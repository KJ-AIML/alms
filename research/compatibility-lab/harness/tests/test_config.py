"""Configuration contract tests."""

from __future__ import annotations

import pytest

from alms_compat.config import ApiFamily, ConfigError, load_endpoint_config, live_preflight
from alms_compat.redact import redact, scan_for_secrets, safe_headers
from alms_compat.urls import BaseUrlError, redirect_host_allowed, validate_base_url


def _base_env(**overrides: str) -> dict[str, str]:
    env = {
        "ALMS_COMPAT_OPENAI_ENDPOINT_ID": "compat-openai-lab",
        "ALMS_COMPAT_OPENAI_MODEL": "synthetic-model",
        "ALMS_COMPAT_OPENAI_BASE_URL": "https://compat.example.test/v1",
        "ALMS_COMPAT_OPENAI_API_KEY": "sk-test-not-real-key-value",
        "ALMS_COMPAT_ALLOWED_HOSTS": "compat.example.test",
        "ALMS_COMPAT_OPENAI_BOUNDARY_KIND": "gateway",
        "ALMS_COMPAT_OPENAI_PROVIDER_CLAIM": "unverified-provider",
        "ALMS_COMPAT_OPENAI_GATEWAY_CLAIM": "unverified-gateway",
    }
    env.update(overrides)
    return env


def test_missing_endpoint_id() -> None:
    env = _base_env()
    del env["ALMS_COMPAT_OPENAI_ENDPOINT_ID"]
    with pytest.raises(ConfigError, match="missing endpoint ID"):
        load_endpoint_config(ApiFamily.OPENAI_COMPATIBLE, env=env)


def test_missing_model() -> None:
    env = _base_env()
    del env["ALMS_COMPAT_OPENAI_MODEL"]
    with pytest.raises(ConfigError, match="missing model"):
        load_endpoint_config(ApiFamily.OPENAI_COMPATIBLE, env=env)


def test_missing_base_url_live() -> None:
    env = _base_env(ALMS_COMPAT_CONFIRM_LIVE="1")
    del env["ALMS_COMPAT_OPENAI_BASE_URL"]
    with pytest.raises(ConfigError, match="missing base URL"):
        live_preflight(ApiFamily.OPENAI_COMPATIBLE, env=env)


def test_invalid_scheme() -> None:
    with pytest.raises(BaseUrlError, match="invalid scheme"):
        validate_base_url(
            "ftp://compat.example.test/v1",
            allowed_hosts={"compat.example.test"},
            live_mode=False,
        )


def test_embedded_credential() -> None:
    with pytest.raises(BaseUrlError, match="embedded credentials"):
        validate_base_url(
            "https://user:pass@compat.example.test/v1",
            allowed_hosts={"compat.example.test"},
            live_mode=True,
        )


def test_host_mismatch() -> None:
    with pytest.raises(BaseUrlError, match="host mismatch"):
        validate_base_url(
            "https://other.example.test/v1",
            allowed_hosts={"compat.example.test"},
            live_mode=True,
        )


def test_redirect_host_change_rejected() -> None:
    assert redirect_host_allowed("compat.example.test", "compat.example.test")
    assert not redirect_host_allowed("compat.example.test", "evil.example.test")


def test_credential_absent_live() -> None:
    env = _base_env(ALMS_COMPAT_CONFIRM_LIVE="1")
    del env["ALMS_COMPAT_OPENAI_API_KEY"]
    with pytest.raises(ConfigError, match="credential absent"):
        live_preflight(ApiFamily.OPENAI_COMPATIBLE, env=env)


def test_live_confirm_absent() -> None:
    env = _base_env()
    with pytest.raises(ConfigError, match="live confirm absent"):
        live_preflight(ApiFamily.OPENAI_COMPATIBLE, env=env)


def test_credential_presence_only_no_value_in_config() -> None:
    cfg = load_endpoint_config(ApiFamily.OPENAI_COMPATIBLE, env=_base_env())
    assert cfg.credential_present is True
    assert "sk-test" not in repr(cfg)
    assert "api_key" not in cfg.evidence_identity()
    assert "base_url" not in cfg.evidence_identity()


def test_credential_value_redaction() -> None:
    secret = "sk-test-not-real-key-value"
    redacted, fields = redact(
        {"authorization": f"Bearer {secret}", "note": f"key={secret}"},
        {secret},
    )
    assert redacted["authorization"] == "<redacted>"
    assert secret not in redacted["note"]
    assert fields


def test_authorization_never_persisted_in_safe_headers() -> None:
    headers = safe_headers(
        {"Authorization": "Bearer sk-test-not-real-key-value", "Content-Type": "application/json"}
    )
    assert headers["Authorization"] == "<redacted>"
    assert headers["Content-Type"] == "application/json"


def test_url_leakage_scan() -> None:
    hits = scan_for_secrets(
        {"request_path": "/v1/chat/completions", "bad": "https://secret.example/v1"}
    )
    assert any("bad" in h for h in hits)


def test_https_required_live() -> None:
    with pytest.raises(BaseUrlError, match="HTTPS"):
        validate_base_url(
            "http://compat.example.test/v1",
            allowed_hosts={"compat.example.test"},
            live_mode=True,
        )


def test_missing_host_allowlist_live() -> None:
    env = _base_env(ALMS_COMPAT_CONFIRM_LIVE="1")
    del env["ALMS_COMPAT_ALLOWED_HOSTS"]
    with pytest.raises(ConfigError, match="missing host allowlist"):
        live_preflight(ApiFamily.OPENAI_COMPATIBLE, env=env)
