from fastapi import FastAPI

app = FastAPI(title="RAG Assistant", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn
    uvicorn.run(app="rag.api:app", host="0.0.0.0", port=8000, reload=True)
