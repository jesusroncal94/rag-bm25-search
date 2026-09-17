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
    prompt_version: str | None
    sources: list[Source]

    @classmethod
    def answered(
        cls,
        answer: str,
        retrieval_confidence: float,
        sources: list[Source],
        prompt_version: str,
    ) -> "AskResponse":
        return cls(
            answer=answer,
            grounded=True,
            reason=None,
            retrieval_confidence=round(retrieval_confidence, 3),
            prompt_version=prompt_version,
            sources=sources,
        )

    @classmethod
    def decline(
        cls,
        reason: DeclineReason,
        retrieval_confidence: float,
        sources: list[Source] | None = None,
        prompt_version: str | None = None,
    ) -> "AskResponse":
        return cls(
            answer=None,
            grounded=False,
            reason=reason,
            retrieval_confidence=round(retrieval_confidence, 3),
            prompt_version=prompt_version,
            sources=sources or [],
        )
