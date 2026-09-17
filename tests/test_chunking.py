from rag.chunking import chunk_document
from rag.corpus import load_corpus

DOCUMENT = """# Card Security Policy

## Blocking a card

A blocked card stops payments within five seconds.

## PIN and card limits

The daily ceiling is 2500 EUR.
"""


def test_one_chunk_per_section():
    chunks = chunk_document("card-security-policy", DOCUMENT)

    assert [chunk.section for chunk in chunks] == ["Blocking a card", "PIN and card limits"]
