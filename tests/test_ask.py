from unittest.mock import patch

from fastapi.testclient import TestClient

from rag.api import app
from rag.model import Generated

client = TestClient(app)


def test_ask_returns_the_contract_fields():
    response = client.post(
        "/ask",
        json={"question": "How do I block my card?"}
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "answer", "grounded", "reason", "retrieval_confidence", "grounding_score",
        "prompt_version", "sources",
    }


def test_a_refusal_carries_no_answer_and_an_explicit_reason():
    body = client.post(
        "/ask",
        json={"question": "How do I block my card?"}
    ).json()

    assert body["answer"] is None
    assert body["reason"] == "insufficient_evidence"


def test_an_answerable_question_is_answered_with_citations():
    body = client.post(
        "/ask",
        json={"question": "what is the SEPA cut-off time"}
    ).json()

    assert body["grounded"] is True
    assert body["reason"] is None
    assert "[payments-and-transfers#sepa-credit-transfer]" in body["answer"]
    assert body["prompt_version"]


def test_a_question_the_corpus_cannot_answer_is_declined_for_lack_of_evidence():
    body = client.post("/ask", json={"question": "how do I apply for a mortgage"}).json()

    assert body["reason"] == "insufficient_evidence"
    assert body["retrieval_confidence"] < 0.30


def test_an_ungrounded_draft_is_withheld_whole():
    uncited = Generated("Blocking a card is instant and refunds are automatic.")

    with patch("rag.api.model.generate", return_value=uncited):
        body = client.post(
            "/ask",
            json={"question": "what is the SEPA cut-off time"}
        ).json()

    assert body["grounded"] is False
    assert body["answer"] is None
    assert body["reason"] == "insufficient_evidence"
    assert body["grounding_score"] == 0.0
