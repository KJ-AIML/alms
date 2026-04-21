def test_sample_agent_flow(client):
    response = client.post("/api/v1/agent/execute", json={"query": "Hello"})
    json_data = response.json()
    assert "success" in json_data
    assert "request_id" in json_data
    if response.status_code == 200:
        assert json_data["success"] is True
        assert "response" in json_data["data"]
    else:
        assert response.status_code == 503
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "AGENT_UNAVAILABLE"
