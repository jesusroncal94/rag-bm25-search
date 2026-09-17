from rag.guardrail import check

RETRIEVED = {"doc#a", "doc#b"}


def test_a_fully_cited_answer_passes():
    result = check(
        "The ceiling is 2500 EUR [doc#a]. A block applies in five seconds [doc#b].",
        RETRIEVED,
        threshold=0.8
    )

    assert result.passed
    assert result.score == 1.0


def test_fluent_prose_with_no_citations_is_withheld():
    result = check(
        "Blocking a card is instant and refunds are processed automatically.",
        RETRIEVED,
        threshold=0.8
    )

    assert not result.passed
    assert result.score == 0.0


def test_an_invented_source_fails_whatever_the_ratio_says():
    result = check(
        "The ceiling is 2500 EUR [doc#a]. Refunds are automatic [doc#invented].",
        RETRIEVED,
        threshold=0.5
    )

    assert not result.passed
    assert result.invented == {"doc#invented"}


def test_coverage_is_counted_per_claim_not_per_answer():
    result = check(
        "Blocking is instant. Refunds are automatic. Limits can be raised [doc#a].",
        RETRIEVED,
        threshold=0.8
    )

    assert result.score == 0.333
    assert not result.passed
