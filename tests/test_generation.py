from rag import prompt
from rag.corpus import load_corpus
from rag.model import FakeModel, Generated, HttpModel

chunks = load_corpus()[:2]


def test_the_prompt_carries_the_chunk_ids():
    rendered = prompt.render("how do I block my card", chunks)

    for chunk in chunks:
        assert f'<chunk id="{chunk.id}">' in rendered


def test_the_model_cites_what_it_was_given():
    generated = FakeModel().generate(
        prompt.render("how do I block my card", chunks)
    )

    assert f"[{chunks[0].id}]" in generated.text


def test_a_provider_failure_is_reported_not_raised():
    broken = HttpModel("http://127.0.0.1:1", "key", "model", timeout=0.2)
    result = broken.generate("anything")

    assert result == Generated("", failed=True)
