from fastapi import FastAPI

from rag import guardrail, prompt
from rag.chunking import Chunk
from rag.config import GROUNDING_THRESHOLD, RETRIEVAL_FLOOR
from rag.confidence import coverage
from rag.contracts import AskRequest, AskResponse, Source
from rag.corpus import load_corpus
from rag.model import build_model
from rag.rewrite import rewrite
from rag.search import BM25Index

SNIPPET_LENGTH = 240

app = FastAPI(title="RAG BM25 Search", version="0.1.0")
index = BM25Index(load_corpus())
model = build_model()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": model.name, "prompt_version": prompt.VERSION}


@app.post("/ask")
def ask(request: AskRequest) -> AskResponse:
    query = rewrite(model, request.question)
    found = index.search(query)

    if not found:
        return AskResponse.decline("insufficient_evidence", 0.0)

    chunks = [chunk for chunk, _ in found]
    confidence = coverage(index, query, chunks[0])
    sources = [to_source(chunk, score) for chunk, score in found]

    if confidence < RETRIEVAL_FLOOR:
        return AskResponse.decline("insufficient_evidence", confidence, sources)

    generated = model.generate(prompt.render(request.question, chunks))

    if generated.failed:
        return AskResponse.decline("model_unavailable", confidence, sources, prompt.VERSION)

    if "INSUFFICIENT_EVIDENCE" in generated.text:
        return AskResponse.decline("insufficient_evidence", confidence, sources, prompt.VERSION)

    grounding = guardrail.check(
        generated.text,
        retrieved={chunk.id for chunk in chunks},
        threshold=GROUNDING_THRESHOLD,
    )

    if not grounding.passed:
        return AskResponse.decline(
            "insufficient_evidence",
            confidence,
            sources,
            prompt.VERSION,
            grounding.score,
        )

    return AskResponse.answered(
        generated.text,
        confidence,
        grounding.score,
        sources,
        prompt.VERSION,
    )


def to_source(chunk: Chunk, score: float) -> Source:
    return Source(
        id=chunk.id,
        title=chunk.title,
        section=chunk.section,
        snippet=chunk.text[:SNIPPET_LENGTH],
        score=round(score, 3),
    )


def main() -> None:
    import uvicorn
    uvicorn.run(app="rag.api:app", host="0.0.0.0", port=8000, reload=True)
