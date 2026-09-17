from typing import Literal

from pydantic import BaseModel, Field

DeclineReason = Literal["insufficient_evidence", "model_unavailable"]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    id: str
    title: str
    section: str
    snippet: str
    score: float


class AskResponse(BaseModel):
    answer: str | None
    grounded: bool
    reason: DeclineReason | None
    retrieval_confidence: float
    sources: list[Source]

    @classmethod
    def decline(
        cls,
        reason: DeclineReason,
        retrieval_confidence: float,
        sources: list[Source] | None = None,
    ) -> "AskResponse":
        return cls(
            answer=None,
            grounded=False,
            reason=reason,
            retrieval_confidence=round(retrieval_confidence, 3),
            sources=sources or [],
        )
