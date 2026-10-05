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
    query = Generated("SEPA cut-off time")
    uncited = Generated("Blocking a card is instant and refunds are automatic.")

    with patch("rag.api.model.generate", side_effect=[query, uncited]):
        body = client.post(
            "/ask",
            json={"question": "what is the SEPA cut-off time"}
        ).json()

    assert body["grounded"] is False
    assert body["answer"] is None
    assert body["reason"] == "insufficient_evidence"
    assert body["grounding_score"] == 0.0


def test_search_uses_the_rewritten_query_and_the_model_reads_the_original_question():
    question = (
        "I sent a transfer this morning and my landlord keeps asking, what is the SEPA "
        "cut-off time"
    )
    query = Generated("SEPA cut-off time")
    cited = Generated(
        "The cut-off is 15:00 CET [payments-and-transfers#sepa-credit-transfer]."
    )

    with patch("rag.api.model.generate", side_effect=[query, cited]) as generate:
        body = client.post("/ask", json={"question": question}).json()

    answer_prompt = generate.call_args_list[1].args[0]

    assert body["grounded"] is True
    assert body["retrieval_confidence"] == 1.0
    assert f"Question: {question}" in answer_prompt


def test_a_failed_rewrite_falls_back_to_the_question_as_asked():
    failed = Generated("", failed=True, error="HTTP 429")
    cited = Generated(
        "The cut-off is 15:00 CET [payments-and-transfers#sepa-credit-transfer]."
    )

    with patch("rag.api.model.generate", side_effect=[failed, cited]):
        body = client.post("/ask", json={"question": "what is the SEPA cut-off time"}).json()

    assert body["grounded"] is True
    assert body["retrieval_confidence"] == 0.703
