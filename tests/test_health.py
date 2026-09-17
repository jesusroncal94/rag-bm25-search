from fastapi.testclient import TestClient

from rag.api import app

client = TestClient(app)


def test_health_reports_what_is_running():
    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["model"]
    assert body["prompt_version"]
