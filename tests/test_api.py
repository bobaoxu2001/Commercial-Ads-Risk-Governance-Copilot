from fastapi.testclient import TestClient

from src.app.api import app

client = TestClient(app)


def test_health_reports_real_data_only() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["real_data_only"] is True
    assert "database_ready" in body


def test_llm_comparison_endpoint_is_safe_without_key() -> None:
    """The endpoint must respond without error and never claim an LLM is available without a key."""
    response = client.get("/api/llm-comparison?limit=3")
    assert response.status_code == 200
    body = response.json()
    assert body["llm_available"] is False
    assert "cases" in body
    assert isinstance(body["cases"], list)
