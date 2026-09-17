from fastapi import FastAPI

from rag.chunking import Chunk
from rag.contracts import AskRequest, AskResponse, Source
from rag.corpus import load_corpus
from rag.search import BM25Index

SNIPPET_LENGTH = 240

app = FastAPI(title="RAG Assistant", version="0.1.0")
index = BM25Index(load_corpus())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask")
def ask(request: AskRequest) -> AskResponse:
    found = index.search(request.question)

    return AskResponse.decline(
        "insufficient_evidence",
        [to_source(chunk, score) for chunk, score in found],
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
