from rag.model import FakeModel, Generated
from rag.rewrite import rewrite


class Replies:
    def __init__(self, generated: Generated) -> None:
        self.generated = generated

    def generate(self, prompt: str) -> Generated:
        return self.generated


def test_the_query_is_the_first_line_without_quotes():
    model = Replies(Generated('"card block stop payments"\nThis query keeps the key terms.'))

    assert rewrite(model, "how long does a card block take") == "card block stop payments"


def test_a_failed_or_empty_rewrite_keeps_the_question():
    question = "what is the SEPA cut-off time"

    assert rewrite(Replies(Generated("", failed=True, error="HTTP 429")), question) == question
    assert rewrite(Replies(Generated("  ")), question) == question


def test_the_stand_in_leaves_the_question_as_it_is():
    assert rewrite(FakeModel(), "what is the SEPA cut-off time") == "what is the SEPA cut-off time"
