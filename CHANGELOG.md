# Changelog

A record of how this service was built, one concept at a time.

Each tagged entry corresponds to a step in the build: something that runs, can be
demonstrated, and adds exactly one idea. Where a number was chosen, the entry says what was
measured to choose it — the point of the exercise was that no threshold is a guess.

The design this implements is in
[docs/Jesus_Roncal_RAG_Solution_Design.pdf](docs/Jesus_Roncal_RAG_Solution_Design.pdf).

---

## Unreleased

### A name that says how it retrieves

**Renamed** the project from `rag-assistant` to `rag-bm25-search`: the package, the script,
the API title and the README.

"Assistant" said nothing about the one decision that shapes everything else here, which is
retrieval by BM25 rather than by embeddings. The name now carries it.

### Documentation, and an image that starts on its own

**Added** a `README.md`, this changelog, and the source design under `docs/`.

The README states the measured gap — 10 of 10 retrieval against 1 of 6 answers on
naturally phrased questions — rather than leaving a reader to find the limits themselves. A
README that lists only what works reads as an omission; one that names its ceiling with the
measurement beside it reads as a decision.

**Fixed** `--export` in the image `CMD`, which should have been `--port`. It never bit because
the compose file overrides the command, so the image had never actually been started on its
own; `docker run` against it failed immediately at startup. A default that is only ever
shadowed is a default nobody has tested.

### Natural-language questions, and a gate on rates instead of counts

**Added** nine holdout questions written the way a customer writes in a chat — long, with
context — tagged `"style": "natural"`. The report now breaks the holdout down by phrasing.

**Changed** the no-regression baseline from counts to rates.

Retrieval finds the right chunk in **6 of 6** natural questions; the service answers **1**.
Confidence is a ratio over every term in the question, so a long question carries more words
the corpus never uses and each one counts against it. The earlier 8-in-10 was an artefact of
the original questions all being terse, having been written by one person in one sitting — a
holdout written that way is not independent of its author.

Adding them also exposed the gate. With a baseline in counts, `answered` rose from 8 to 9
because the set grew, and the gate passed while the answered rate fell from **0.800 to 0.562**.
It approved the regression it exists to catch. A gate on counts is only valid while the
dataset never changes, which is never.

### Load `.env`, and record why a provider call failed

**Fixed** the environment file never being read: a `.env` is only text, and Docker Compose
substitutes it inside the compose file without injecting it into the container. `env_file`
does.

**Added** `Generated.error`, which records the cause of a provider failure. `HTTP 429`,
`HTTP 401` and a timeout need three different fixes.

**Changed** the evaluator to count provider failures separately from quality failures, to
accept `--pace` for staying under a rate limit, and to refuse to render a verdict at all when
any call failed.

Found by running against a real model for the first time: **HTTP 429 on 28 of 32 calls**, every
one of them counted as a wrong answer. That is the most expensive way to lose a day — tuning a
prompt to fix a rate limit.

The same run verified two things that a deterministic stand-in cannot: the citation format the
guardrail parses is one a real model actually produces, and the prompt-injection line planted
in the corpus did not steer the answer.

---

## [step-7] Evaluation and the gate

**Added** `evaluation/`: 32 questions in two splits, run through the real endpoint, and one
exit code.

`dev` holds the sixteen questions the thresholds were tuned on; `holdout` was written
afterwards and never used to choose anything. The gap is the result: dev declines **6 of 6**
unanswerable questions, holdout **5 of 6**. The 6 of 6 was the tuning looking at itself.

No floor fixes it. Reaching 6 of 6 on holdout needs 0.35, which costs four answerable
questions in ten. Retrieval is **10 of 10 on both splits**, so everything that fails, fails
after it — the defect is in the confidence measure, not the threshold or the retriever.

The gate mixes absolute limits with no-regression against a recorded baseline, and prints
unmet targets as `OPEN`. A gate that is red from the first run is a gate everyone learns to
ignore, and a target hidden in a backlog is a target nobody meets.

## [step-6] Citation guardrail

**Added** `rag/guardrail.py` and `grounding_score` to the response. An answer reaches the user
only when enough of its claims cite a chunk that was actually retrieved; below the threshold
the draft is withheld whole.

Handing back the cited half would ask the reader to work out which half was supported, which
is the job this service exists to do for them.

It checks citations, not truth. Whether the cited chunk *supports* the claim needs a model, and
a model on the request path costs what the answer just cost. What it catches is the common
shape of a hallucination: fluent prose with no source, or with a source that does not exist. An
invented id fails outright whatever the ratio says, because it looks verifiable and so nobody
checks it.

The threshold of 0.8 was chosen by scoring seven hand-written answer shapes: a fully cited
answer scores 1.00, one uncited claim in five scores 0.75, a single citation at the end of
three claims scores 0.33.

**Fixed** a defect this step found in step 5: the model wrote `"Sentence. [id]"`, so splitting
on sentence boundaries orphaned the citation from its claim and scored a correct answer at
**0.5**. Fixed at the source, in the prompt rule and the stand-in. The citation format is a
contract between the prompt and the check.

**Changed** `CLAIM_WORDS` from 4 to 3 after measuring: at 4, an answer with two uncited
three-word claims and one citation scored **1.00**.

## [step-5] Generation with citations

**Added** `rag/prompt.py` and `rag/model.py`. `/ask` answers when the evidence clears the
floor, and the prompt version travels with every answer so a regression can be traced to the
change that caused it.

Without `MODEL_API_KEY` the service uses a deterministic stand-in. That is what keeps the tests
hermetic and CI free: a suite that calls a live model tests the provider's mood, not the code.
With a key, any OpenAI-compatible endpoint works.

A provider failure is a product state, not an exception — it becomes a declined answer with the
sources attached. There is no retry loop, because the latency budget is fixed.

`prompt_version` is null when no model was called, which separates "the corpus has nothing"
from "the model produced nothing". Two failures with different owners.

## [step-4] Retrieval confidence floor

**Added** `rag/config.py`, `rag/confidence.py`, and `retrieval_confidence` in the response. A
question whose evidence is too weak is declined instead of answered, with the closest sources
still attached so a refusal carries something to read.

Confidence is rarity-weighted term coverage, **not** the BM25 score. A raw score is not
comparable between questions: it grows with query length and term rarity, so one threshold
cannot serve both a three-word and a nine-word question.

Measured over 10 answerable and 6 unanswerable questions, taking the highest threshold that
declines all 6:

| Measure | Answers | Declines |
|---|---|---|
| Raw BM25 score | 7 of 10 | 6 of 6 |
| Score per term | 7 of 10 | 6 of 6 |
| Score over its own maximum | 5 of 10 | 6 of 6 |
| **Rarity-weighted coverage** | **9 of 10** | **6 of 6** |

The floor is 0.30, from the gap between the best unanswerable (0.281) and the second worst
answerable (0.309). That window is 0.028 wide on sixteen hand-written questions: enough not to
invent the number, not enough to trust it.

## [step-3] Lexical search

**Added** `rag/search.py` — BM25 over the chunks — and `score` on each source. `/ask` returns
real sources. It still declines every question: nothing generates text yet.

Measured against four alternatives on five questions with known answers. `K1` earns its place,
buying the one extra top-1 hit over TF-IDF by stopping a chunk from winning on repetition. `B`
does not: chunks here run 46 to 99 tokens, so `b=0` scores identically. It stays at the
conventional value until a corpus with uneven sections arrives.

A zero score is dropped and a low score is not. Zero means no query term appeared — that is not
a weak match, it is not a match. But deciding that 1.04 is too weak to act on is a product
decision, and it belongs to the confidence floor.

## [step-2] Corpus and chunking

**Added** `rag/chunking.py`, `rag/corpus.py`, and four synthetic banking documents, one of
which carries a planted prompt-injection line as a test case.

Markdown documents split into one chunk per section. The chunk id is `document#section`, so a
citation points at something a reader can open — nobody verifies `policy-142#chars-4000-4500`.

No token budget and no overlap: the longest section here is about 150 words, so a size would be
a guess with nothing measuring it.

Splitting on a pattern with a capture group keeps the headings, which removes the position
arithmetic entirely. Duplicate ids are guarded by a test rather than by code, because the
failure is detectable and not urgent — and a test fails loudly where the code would have
invented a suffix in silence.

## [step-1] The response contract

**Added** `rag/contracts.py`. `POST /ask` returns the four contract fields and always declines,
because there is no corpus yet: with nothing indexed, `insufficient_evidence` is the truthful
answer rather than a placeholder.

A refusal is a 200, not an error. Returning 4xx would force every client to treat a normal
product state as a failure, and to reimplement the difference between "I don't know" and "I am
down".

Fields arrive when a step can fill them, so no field is permanently null. A field that is
always null cannot be told apart from one that does not apply to this answer.

Authentication is deliberately absent: it is a second concept, and the rule of this build is
one per step.

## [step-0] Skeleton that runs

**Added** a FastAPI service with a single `/health` endpoint, a Dockerfile, and one test.

No configuration module: nothing needs configuring at this point, and a settings file full of
unused values hides which ones are actually in use.
