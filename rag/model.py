import re

from dataclasses import dataclass

import httpx2

from rag.config import MODEL_API_KEY, MODEL_BASE_URL, MODEL_NAME, MODEL_TIMEOUT_SECONDS

CHUNK_ID = re.compile(r'<chunk id="([^"]+)">\n(.*?)\n</chunk>', re.DOTALL)
FIRST_SENTENCE = re.compile(r"^.*?[.!?](?=\s|$)")
QUESTION = re.compile(r"^Question: (.*)$", re.MULTILINE)


@dataclass(frozen=True)
class Generated:
    text: str
    failed: bool = False
    error: str | None = None


class FakeModel:
    name = "fake"

    def generate(self, prompt: str) -> Generated:
        chunks = CHUNK_ID.findall(prompt)

        if not chunks:
            question = QUESTION.search(prompt)

            return Generated(question.group(1) if question else "INSUFFICIENT_EVIDENCE")

        sentences = []

        for chunk_id, text in chunks[:2]:
            match = FIRST_SENTENCE.match(text.strip())
            sentence = (match.group() if match else text.strip()).rstrip(".!?")
            sentences.append(f"{sentence} [{chunk_id}].")

        return Generated(" ".join(sentences))


class HttpModel:
    def __init__(self, base_url: str, api_key: str, name: str, timeout: float) -> None:
        self.name = name
        self.client = httpx2.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def generate(self, prompt: str) -> Generated:
        try:
            response = self.client.post(
                "/chat/completions",
                json={
                    "model": self.name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
            )
            response.raise_for_status()

            return Generated(response.json()["choices"][0]["message"]["content"].strip())
        except httpx2.HTTPStatusError as exc:
            return Generated("", failed=True, error=f"HTTP {exc.response.status_code}")
        except httpx2.HTTPError as exc:
            return Generated("", failed=True, error=type(exc).__name__)


def build_model():
    if not MODEL_API_KEY:
        return FakeModel()

    return HttpModel(MODEL_BASE_URL, MODEL_API_KEY, MODEL_NAME, MODEL_TIMEOUT_SECONDS)
