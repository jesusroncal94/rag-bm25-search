from rag.confidence import coverage
from rag.config import RETRIEVAL_FLOOR
from rag.corpus import load_corpus
from rag.search import BM25Index

index = BM25Index(load_corpus())


def best_confidence(question: str) -> float:
    found = index.search(question)
    return coverage(index, question, found[0][0]) if found else 0.0


def test_coverage_is_a_ratio():
    assert 0.0 <= best_confidence("what is the SEPA cut-off time") <= 1.0


def test_an_answerable_question_clears_the_floor():
    assert best_confidence("what is the SEPA cut-off time") >= RETRIEVAL_FLOOR
    assert best_confidence("when does a contactless payment need a PIN") >= RETRIEVAL_FLOOR


def test_a_question_the_corpus_cannot_answer_falls_below_the_floor():
    assert best_confidence("what interest rate do you pay on savings") < RETRIEVAL_FLOOR
    assert best_confidence("how do I apply for a mortgage") < RETRIEVAL_FLOOR
