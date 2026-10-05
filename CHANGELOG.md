# Changelog

A record of how this service was built, one concept at a time.

Each tagged entry corresponds to a step in the build: something that runs, can be
demonstrated, and adds exactly one idea. Where a number was chosen, the entry says what was
measured to choose it — the point of the exercise was that no threshold is a guess.

The design this implements is in
[docs/Jesus_Roncal_RAG_Solution_Design.pdf](docs/Jesus_Roncal_RAG_Solution_Design.pdf).

---

## Unreleased

### One baseline per model, and the rewrite's holdout result

**Changed** the no-regression baseline to one set of rates per model, and the gate to compare a
run against the baseline of the model that produced it.

The gain from the rewrite only exists with a real model; the stand-in leaves the question as it
is. With a single baseline at the new rates, every offline run — the free, hermetic one — would
fail the gate forever. Leaving it at the old rates would let a real run lose the whole gain and
stay green. So the stand-in keeps **0.562** answered and **0.889** declined, which still guards
retrieval and confidence, and `qwen/qwen3.8-27b` gets the rates of its first holdout run:
answered **0.875**, declined **1.000**, retrieval 1.0. A model with no entry gets no regression
check, and says so.

Holdout, both columns with `qwen/qwen3.8-27b`, each run once with no provider failures:

| holdout | Answered, before → after | Declined when it must, before → after |
|---|---|---|
| Terse | 8 → 9 of 10 | 6 → 6 of 6 |
| Natural | **1 → 5 of 6** | 3 → 3 of 3 |
| Overall | 0.562 → **0.875** | 1.000 → 1.000 |

The "after" was run once, after every choice had been made on dev. The "before" is the code
just ahead of the rewrite, run on holdout afterwards with the same model and nothing changed.

That second run corrected a claim. Against the published baseline, declines seemed to rise from
0.889 to 1.000, with "how do I set up a standing order" no longer getting through. But that
0.889 came from the stand-in, which answers anything that clears the floor; `qwen` already
declined the standing order before the rewrite existed. The decline rate is the model's, not
the rewrite's. **What the rewrite bought is answers — 9 to 14 of 16 — at no cost in declines.**

Both remaining misses are the floor, not the model: "do I get provisional credit when an item
never arrived" at 0.297, and a transfer that "bounces back" at 0.142 — the corpus says
*returned*, and the rewrite is told not to add words.

The `qwen` entry was written by hand from that run rather than by `--record`, which would have
spent another 110 calls to measure the same thing. `--record` now writes only the entry of the
model it ran with.

**Changed** the evaluator's advice on a rate limit from `--pace 2.5` to `--pace 10`: each
question now makes two calls, and the free tier refused generation calls at 2.5 seconds apart.

### The model rewrites the question before the search

**Added** `rag/rewrite.py`. Before searching, the model reduces the question to the words that
name what is being asked; search and confidence run on that query, while the answer is still
written for the question as asked, since the rewrite drops context the answer may need. If the
rewrite fails, the search runs on the original question — at worst, the service behaves as it
did before. Retrieval is still BM25 alone.

**Changed** the answering prompt to `1.1`: when the chunks do not answer, reply with exactly
`INSUFFICIENT_EVIDENCE` and nothing else, and never cite a chunk to say it is missing. The
version covers both prompts.

Measured on the dev split with `qwen/qwen3.8-27b`, floor unchanged at 0.30:

| dev | Answered (terse · natural) | Declined when it must |
|---|---|---|
| Before | 9/10 · 0/8 | 12/12 |
| Rewrite, prompt 1.0 | 10/10 · 6/8 | 11/12 |
| **Rewrite, prompt 1.1** | **10/10 · 6/8** | **12/12** |

The rewrite alone does not separate anything: it raises the confidence of unanswerable questions
too — "mortgage application" goes from 0.18 to 0.41 — and with the floor as the only filter,
declining all twelve leaves 8 answered instead of 9. It works because the floor is not the only
filter: the model declined four of the five unanswerable questions that passed it.

The fifth exposed a defect older than the rewrite. Asked about joint accounts, the model refused
in its own words and cited a chunk to say so — "The provided chunks do not contain information
regarding the opening of a joint account [account-and-verification#eligibility]" — and the
guardrail, which checks citations, passed it as a grounded answer. A refusal with a citation
looks exactly like an answer. Fixed in the prompt rather than by matching refusal phrases,
which would be one more list tuned by hand.

The cost is a second model call per question, before the search. A full evaluation run doubles
to about 110 calls, and the generation calls hit the free tier's limit at 2.5 seconds apart; 6
held. The stand-in leaves the question as it is, so tests stay hermetic and offline runs measure
what they did before — but the gain only exists with a real model, and only a real run measures
it.

### Stopwords and stemming in confidence, measured and set aside

**Measured** two lexical changes to confidence on the dev split, and kept neither. Both use
off-the-shelf parts — NLTK's English stopword list, unedited, and the Snowball stemmer — so the
list itself is not one more thing tuned by hand.

| dev | Gold in top 1 (terse · natural) | Answered at 0.30 (terse · natural) | Declined at 0.30 | Answered, floor declining all 12 |
|---|---|---|---|---|
| Current | 8/10 · 4/8 | 9/10 · **0/8** | 12/12 | 9/10 · 0/8 |
| Stopwords out of confidence | 8/10 · 4/8 | 9/10 · 0/8 | 9/12 | 6/10 · 0/8 |
| … and out of search | 9/10 · 5/8 | 9/10 · 0/8 | 9/12 | 6/10 · 0/8 |
| … and stemmed | **10/10 · 7/8** | 9/10 · 0/8 | 9/12 | 2/10 · 0/8 |

Stopwords were only half of the diagnosis. What sinks a natural question is the customer's own
situation — *concert*, *tickets*, *landlord*, *hotel*, *daughter* — and with the stopwords gone
those words weigh even more. Meanwhile a short unanswerable question collapses to its content
words: "how do I apply for a mortgage" becomes *apply mortgage*, *apply* is in the corpus, and
confidence reaches 0.50.

Two other measures went the same way. Absolute matched rarity, rather than a ratio, answers 3
natural questions in 8 but costs 2 terse ones — 10 of 18 against 9, too small a difference on
this many questions to trust. A ratio over only the terms the corpus knows scores "what interest
rate do you pay on savings" at 1.000.

Any measure that compares the question's words with the corpus's penalises the customer's
vocabulary. Stemming does lift the right chunk to the top, but it changes no answer, because
the model already reads the top five.

### Natural questions in dev, so the fix can be chosen without looking at holdout

**Added** fourteen dev questions phrased the way a customer writes — eight answerable, six not
— and a per-phrasing breakdown of dev in the report.

Every natural question was in holdout. Choosing a change to confidence by how it moved those
nine would have tuned on the split that exists to be untouched. The answerable ones point at
sections no natural holdout question uses; the unanswerable ones sit deliberately close to the
corpus vocabulary — card limits, currency, a new device — so a change that simply raises
confidence across the board shows up as a false answer.

The baseline they set, with the deterministic stand-in:

| dev | Gold in top 5 | Gold in top 1 | Answered | Declined when it must |
|---|---|---|---|---|
| Terse | 10 of 10 | — | 9 of 10 | 6 of 6 |
| Natural | 7 of 8 | 4 of 8 | **0 of 8** | 6 of 6 |

Answerable natural questions score 0.087 to 0.179 and unanswerable ones 0.075 to 0.154, so no
floor separates them; the measure has to change, not the threshold. The cause is visible term
by term: a word the corpus never uses gets the highest rarity, and the corpus is written in the
third person, so "I", "my", "how" and "what" weigh most in the ceiling of every question a
customer writes.

**Changed** the evaluator to ask each question once. The per-phrasing breakdown asked the
holdout questions a second time, which would have meant 96 provider calls on a 55-question
run; it now reuses the answers it already has.

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
