from rag.corpus import load_corpus
from rag.search import BM25Index, tokenize

index = BM25Index(load_corpus())


def test_tokenize_lowercases_and_keeps_alphanumerics():
    assert tokenize("SEPA, 1.7% transfers!") == ["sepa", "1", "7", "transfers"]


def test_a_question_the_corpus_cannot_answer_scores_far_lower():
    """Nothing here is about mortgages: only the word "in" matches anything at all.
    Search still returns something, because deciding that a score is too low to act
    on is the confidence floor's job in step 4, not the retriever's."""
    unanswerable = index.search("mortgage interest rates in portugal")[0][1]
    answerable = index.search("how long does a card block take")[0][1]

    assert unanswerable < answerable / 3


def test_results_come_back_best_first():
    scores = [score for _, score in index.search("chargeback dispute provisional credit")]

    assert scores == sorted(scores, reverse=True)
