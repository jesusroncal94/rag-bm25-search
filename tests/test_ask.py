from fastapi.testclient import TestClient

from rag.api import app

client = TestClient(app)


def test_ask_returns_the_contract_fields():
    response = client.post(
        "/ask",
        json={"question": "How do I block my card?"}
    )

    assert response.status_code == 200
    assert set(response.json()) == {"answer", "grounded", "reason", "sources"}


def test_a_refusal_carries_no_answer_and_an_explicit_reason():
    body = client.post(
        "/ask",
        json={"question": "How do I block my card?"}
    ).json()

    assert body["answer"] is None
    assert body["reason"] == "insufficient_evidence"
