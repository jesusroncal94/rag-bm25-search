from fastapi import FastAPI

from rag.contracts import AskRequest, AskResponse

app = FastAPI(title="RAG Assistant", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask")
def ask(request: AskRequest) -> AskResponse:
    return AskResponse.decline("insufficient_evidence")


def main() -> None:
    import uvicorn
    uvicorn.run(app="rag.api:app", host="0.0.0.0", port=8000, reload=True)
