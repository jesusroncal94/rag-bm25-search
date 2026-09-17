import re

from dataclasses import dataclass, field

CITATION = re.compile(r"\[([^\][\s]+)\]")
SENTENCE = re.compile(r"(?<=[.!?])\s+")

CLAIM_WORDS = 3


@dataclass(frozen=True)
class Grounding:
    score: float
    passed: bool
    invented: set[str] = field(default_factory=set)


def check(answer: str, retrieved: set[str], threshold: float) -> Grounding:
    claims = [
        sentence
        for sentence in SENTENCE.split(answer.strip())
        if len(sentence.split()) >= CLAIM_WORDS
    ]

    if not claims:
        return Grounding(score=0.0, passed=False)

    invented: set[str] = set()
    supported = 0

    for claim in claims:
        cited = set(CITATION.findall(claim))
        invented |= cited - retrieved

        if cited & retrieved:
            supported += 1

    score = supported / len(claims)

    return Grounding(
        score=round(score, 3),
        passed=score >= threshold and not invented,
        invented=invented,
    )
