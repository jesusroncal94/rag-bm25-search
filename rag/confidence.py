from rag.chunking import Chunk
from rag.search import BM25Index, tokenize


def coverage(index: BM25Index, question: str, chunk: Chunk) -> float:
    terms = set(tokenize(question))
    ceiling = sum(index.rarity(term) for term in terms)
    if not ceiling:
        return 0.0

    present = set(tokenize(chunk.section + " " + chunk.text))
    return sum(index.rarity(term) for term in terms if term in present) / ceiling
