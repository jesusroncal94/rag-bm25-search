from pathlib import Path

from rag.chunking import Chunk, chunk_document

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"


def load_corpus(directory: Path = CORPUS_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []

    for path in sorted(directory.glob("*.md")):
        chunks.extend(
            chunk_document(path.stem, path.read_text(encoding="utf-8"))
        )

    return chunks


if __name__ == "__main__":
    for chunk in load_corpus():
        print(f"{chunk.id:<55} {chunk.text.splitlines()[0][:60]}...")
