from fastapi.testclient import TestClient

from rag.api import app

client = TestClient(app)


def test_ask_returns_the_contract_fields():
    response = client.post(
        "/ask",
        json={"question": "How do I block my card?"}
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "answer", "grounded", "reason", "retrieval_confidence", "sources",
    }


def test_a_refusal_carries_no_answer_and_an_explicit_reason():
    body = client.post(
        "/ask",
        json={"question": "How do I block my card?"}
    ).json()

    assert body["answer"] is None
    assert body["reason"] == "insufficient_evidence"


def test_an_answerable_question_reaches_the_model_branch():
    body = client.post("/ask", json={"question": "what is the SEPA cut-off time"}).json()

    assert body["reason"] == "model_unavailable"
    assert body["sources"], "a decline still hands back what was found"


def test_a_question_the_corpus_cannot_answer_is_declined_for_lack_of_evidence():
    body = client.post("/ask", json={"question": "how do I apply for a mortgage"}).json()

    assert body["reason"] == "insufficient_evidence"
    assert body["retrieval_confidence"] < 0.30
