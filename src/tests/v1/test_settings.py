import pytest

from src.config.settings import settings


def test_validate_passes_in_debug_mode(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    settings.validate_production_settings()  # must not raise


def test_validate_raises_on_placeholder_secret_key(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "SECRET_KEY", "your-default-secret-key")
    monkeypatch.setattr(settings, "ALLOWED_HOSTS", ["localhost"])
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    with pytest.raises(ValueError, match="SECRET_KEY"):
        settings.validate_production_settings()


def test_validate_raises_on_wildcard_allowed_hosts(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "SECRET_KEY", "secure-key")
    monkeypatch.setattr(settings, "ALLOWED_HOSTS", ["*"])
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    with pytest.raises(ValueError, match="ALLOWED_HOSTS"):
        settings.validate_production_settings()


def test_validate_raises_on_ai_enabled_without_key(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "SECRET_KEY", "secure-key")
    monkeypatch.setattr(settings, "ALLOWED_HOSTS", ["example.com"])
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "MODEL_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        settings.validate_production_settings()


def test_validate_passes_with_safe_production_settings(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "SECRET_KEY", "secure-key-12345")
    monkeypatch.setattr(settings, "ALLOWED_HOSTS", ["example.com"])
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    settings.validate_production_settings()  # must not raise
