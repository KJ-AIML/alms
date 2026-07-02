"""Tests for APIKeyMiddleware's key comparison behavior."""

from fastapi.testclient import TestClient

from src.api.main import app
from src.config.settings import settings


def _client_with_enforced_auth(monkeypatch, api_key="secret-key-123"):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "X_API_KEY", api_key)
    return TestClient(app)


# A protected-but-nonexistent path: the auth middleware runs before
# routing, so it still 401s a bad key here regardless of which optional
# routers (metrics/agents/etc.) are registered for the active profile.
_PROTECTED_PATH = "/api/v1/__auth_probe__"


def test_correct_api_key_is_accepted(monkeypatch):
    client = _client_with_enforced_auth(monkeypatch)
    response = client.get(_PROTECTED_PATH, headers={"X-API-KEY": "secret-key-123"})
    assert response.status_code == 404  # past auth, no such route


def test_incorrect_api_key_is_rejected(monkeypatch):
    client = _client_with_enforced_auth(monkeypatch)
    response = client.get(_PROTECTED_PATH, headers={"X-API-KEY": "wrong-key"})
    assert response.status_code == 401


def test_missing_api_key_is_rejected(monkeypatch):
    client = _client_with_enforced_auth(monkeypatch)
    response = client.get(_PROTECTED_PATH)
    assert response.status_code == 401


def test_public_paths_skip_auth(monkeypatch):
    client = _client_with_enforced_auth(monkeypatch)
    response = client.get("/")
    assert response.status_code == 200
