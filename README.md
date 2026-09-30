# RAG BM25 Search

A question answering service over internal documents. It answers with verifiable citations,
and it declines explicitly when the documents do not support an answer — a refusal returns the
closest sources rather than an apology.

Built one step at a time from the design in
[docs/Jesus_Roncal_RAG_Solution_Design.pdf](docs/Jesus_Roncal_RAG_Solution_Design.pdf). Each
step, and the measurement behind every threshold, is in [CHANGELOG.md](CHANGELOG.md).

## Run

```bash
uv run uvicorn rag.api:app --port 8000
```

Or in a container:

```bash
docker compose up -d
```

Either way the interactive API is at <http://localhost:8000/docs>.

## Try it

A question the corpus answers:

```bash
curl -X POST localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"what is the SEPA cut-off time"}'
```

```json
{ "answer": "A standard SEPA Credit Transfer sent before the cut-off time of 15:00 CET on a
             business day reaches the beneficiary bank on the next business day
             [payments-and-transfers#sepa-credit-transfer]. ...",
  "grounded": true, "reason": null, "retrieval_confidence": 0.703, "grounding_score": 1.0 }
```

One it does not:

```bash
curl -X POST localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"how do I apply for a mortgage"}'
```

```json
{ "answer": null, "grounded": false, "reason": "insufficient_evidence",
  "retrieval_confidence": 0.177, "sources": [ ... ] }
```

Both are `200`. A refusal is a product state, not a transport error, and it still carries the
sources so the reader can judge for themselves.

## Tests and evaluation

```bash
uv run pytest -q
```

```bash
uv run python -m evaluation.run
```

The evaluation runs 41 questions through the real endpoint and exits non-zero on a regression.
`--sweep` shows what other retrieval floors would cost; `--record` moves the baseline, which
should be a deliberate act in its own commit.

## What is where

| Path | |
|---|---|
| `rag/api.py` | The endpoint. Six ways out, in the order they are decided.  |
| `rag/search.py` | BM25 over the chunks. |
| `rag/confidence.py` | How far the retrieved evidence can be trusted. |
| `rag/guardrail.py` | Whether the answer is held up by what was retrieved. |
| `rag/prompt.py` | The prompt, versioned. Its version travels with every answer. |
| `rag/model.py` | A deterministic stand-in, or any OpenAI-compatible endpoint. |
| `rag/config.py` | Every threshold. Each one arrived when a step needed it. |
| `evaluation/` | The question set, the metrics, and the gate. |
| `corpus/` | Four synthetic banking documents, one carrying a planted prompt injection. |

## Where it actually stands

Measured on the holdout split, which was written after the thresholds were chosen and never
used to pick anything:

| | Gold chunk retrieved | Answered when it could |
|---|---|---|
| Terse questions | 10 of 10 | 8 of 10 |
| Questions phrased the way a customer writes | 6 of 6 | **1 of 6** |

**Retrieval is perfect and answering is not.** Confidence is a ratio over every term in the
question, so a long, natural question carries more words the corpus never uses and each one
counts against it. No threshold fixes this: reaching every unanswerable question costs four
answerable ones in ten.

The cause is that a bag of words cannot tell that "block" and "stops payments" are the same
idea. Raising the ceiling needs dense retrieval or reranking, both deliberately out of scope
here. The gap is left in place and reported on every run rather than hidden.

## Using a real model

Without a key the service uses a deterministic stand-in, which is what keeps the tests
hermetic and CI free. To use a real one, put the credentials in `.env`:

```
MODEL_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=llama-3.3-70b-versatile
MODEL_API_KEY=
```

```bash
uv run --env-file .env uvicorn rag.api:app --port 8000
```

Keep the flag explicit rather than exporting the file globally: `uv run pytest` would then hit
the provider on every run, which costs money and makes the suite depend on a provider's mood.

A free tier will rate-limit a full evaluation run. Use `--pace 2.5` to stay under it — and note
that the evaluator refuses to render a verdict at all if any call failed, because a run the
provider refused measured nothing.
