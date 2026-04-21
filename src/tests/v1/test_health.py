def test_root_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.json()["service"] == "ALMS"


def test_v1_live_health_check_without_auth(client_no_auth):
    response = client_no_auth.get("/api/v1/health/live")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "alive"
    assert json_data["data"]["ready"] is True
    assert "request_id" in json_data


def test_v1_ready_health_check_without_auth(client_no_auth, monkeypatch):
    from src.api.endpoints.v1 import health

    async def fake_check_database_connection():
        return True

    monkeypatch.setattr(
        health,
        "check_database_connection",
        fake_check_database_connection,
    )

    response = client_no_auth.get("/api/v1/health/ready")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "ready"
    assert json_data["data"]["dependencies"]["database"] == "healthy"
    assert "request_id" in json_data


def test_v1_ready_health_returns_503_when_database_fails(client_no_auth, monkeypatch):
    from src.api.endpoints.v1 import health

    async def fake_check_database_connection():
        return False

    monkeypatch.setattr(
        health,
        "check_database_connection",
        fake_check_database_connection,
    )

    response = client_no_auth.get("/api/v1/health/ready")
    assert response.status_code == 503
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["data"]["status"] == "degraded"
    assert json_data["data"]["dependencies"]["database"] == "unhealthy"
