import re
from dataclasses import dataclass

HEADING = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    title: str
    section: str
    text: str


def chunk_document(doc_id: str, markdown: str) -> list[Chunk]:
    _, *parts = HEADING.split(markdown)

    if len(parts) < 2:
        return []

    title, _, *sections = parts

    return [
        Chunk(
            id=f"{doc_id}#{slugify(section)}",
            doc_id=doc_id,
            title=title.strip(),
            section=section.strip(),
            text=text.strip(),
        )
        for section, text in zip(sections[::2], sections[1::2])
        if text.strip()
    ]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
