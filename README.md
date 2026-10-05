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

The evaluation runs 55 questions through the real endpoint and exits non-zero on a regression.
The baseline is kept per model, and a run is compared with the baseline of the model that
produced it. `--sweep` shows what other retrieval floors would cost; `--record` moves the
baseline of the model it ran with, which should be a deliberate act in its own commit.

## What is where

| Path | |
|---|---|
| `rag/api.py` | The endpoint. Six ways out, in the order they are decided.  |
| `rag/rewrite.py` | The question reduced to a search query, falling back to the question as asked. |
| `rag/search.py` | BM25 over the chunks. |
| `rag/confidence.py` | How far the retrieved evidence can be trusted. |
| `rag/guardrail.py` | Whether the answer is held up by what was retrieved. |
| `rag/prompt.py` | The prompts, versioned together. The version travels with every answer. |
| `rag/model.py` | A deterministic stand-in, or any OpenAI-compatible endpoint. |
| `rag/config.py` | Every threshold. Each one arrived when a step needed it. |
| `evaluation/` | The question set, the metrics, and the gate. |
| `corpus/` | Four synthetic banking documents, one carrying a planted prompt injection. |

## Where it actually stands

Measured with `qwen/qwen3.8-27b` on the holdout split, which was written after every choice was
made and never used to pick anything:

| | Gold chunk retrieved | Answered when it could | Declined when it must |
|---|---|---|---|
| Terse questions | 10 of 10 | 9 of 10 | 6 of 6 |
| Questions phrased the way a customer writes | 6 of 6 | **5 of 6** | 3 of 3 |

Before the model rewrote the question, natural phrasing answered **1 of 6**. Confidence is a ratio
over every term in the question, so a customer's own words — the hotel, the landlord, "I" and
"my", which a policy written in the third person never uses — counted against it. Stopwords,
stemming and two other confidence measures did not close the gap; the changelog has the numbers.
What did is letting the model reduce the question to its key terms before the search, while the
answer is still written for the question as asked. Retrieval is still BM25 alone.

What it costs, and what it does not fix:

- **A second model call per question**, before the search. The rewrite spends latency the
  answer used to have to itself, and a full evaluation run makes about 110 calls.
- **The gain needs a real model.** The stand-in leaves the question as it is, so offline runs
  still answer 9 of 16 holdout questions; they guard retrieval and confidence, not the rewrite.
- **A word the corpus never uses still loses.** A transfer that "bounces back" scores 0.142,
  because the corpus says *returned* and the rewrite is told not to add words. Another question
  misses the floor by 0.003.
- **It rests on the model declining.** Rewritten, some unanswerable questions clear the floor —
  "mortgage application" scores 0.41 — and are stopped by the model answering
  `INSUFFICIENT_EVIDENCE`. Every unanswerable question in dev and holdout was declined, on one
  run each; that is a behaviour of this model, measured, not a guarantee.

## Using a real model

Without a key the service uses a deterministic stand-in, which is what keeps the tests
hermetic and CI free. To use a real one, put the credentials in `.env`:

```
MODEL_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=qwen/qwen3.8-27b
MODEL_API_KEY=
```

```bash
uv run --env-file .env uvicorn rag.api:app --port 8000
```

Keep the flag explicit rather than exporting the file globally: `uv run pytest` would then hit
the provider on every run, which costs money and makes the suite depend on a provider's mood.

A free tier will rate-limit a full evaluation run. Each question makes two calls, one to
rewrite it and one to answer it; use `--pace 10` to stay under the limit — and note
that the evaluator refuses to render a verdict at all if any call failed, because a run the
provider refused measured nothing.
