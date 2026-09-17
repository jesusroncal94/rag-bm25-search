import math
import re

from collections import Counter

from rag.chunking import Chunk

WORD = re.compile(r"[a-z0-9]+")

K1 = 1.5
B = 0.75


def tokenize(text: str) -> list[str]:
    return WORD.findall(text.lower())


class BM25Index:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        tokens = [tokenize(chunk.section + " " + chunk.text) for chunk in chunks]
        self.frequencies = [Counter(chunk_tokens) for chunk_tokens in tokens]
        self.lengths = [len(chunk_tokens) for chunk_tokens in tokens]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 1.0
        self.chunks_containing = Counter(
            term for chunk_tokens in tokens for term in set(chunk_tokens)
        )

    def search(self, query: str, limit: int = 5) -> list[tuple[Chunk, float]]:
        terms = tokenize(query)
        scored = [
            (chunk, self.score(terms, position))
            for position, chunk in enumerate(self.chunks)
        ]
        matches = [(chunk, score) for chunk, score in scored if score > 0]

        return sorted(matches, key=lambda pair: -pair[1])[:limit]

    def score(self, terms: list[str], position: int) -> float:
        frequencies = self.frequencies[position]
        length = self.lengths[position]
        total = 0.0

        for term in terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            saturation = K1 * (1 - B + B * length / self.average_length)
            total += self.rarity(term) * frequency * (K1 + 1) / (frequency + saturation)

        return total

    def rarity(self, term: str) -> float:
        containing = self.chunks_containing[term]
        return math.log(1 + (len(self.chunks) - containing + 0.5) / (containing + 0.5))
