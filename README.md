# Epictetus, Resurrected

A voice agent you have a real spoken conversation with. He is Epictetus — born a
slave, lamed, exiled from Rome, and now sitting somewhere in 2026 being asked
about a job he hates and a father he is not speaking to.

Everything he says is checked against his own recorded teaching first. The
*Discourses* are indexed, searched on **every single turn**, and the passages he
drew on appear beside the conversation as he speaks. He never cites them out
loud — nobody quotes chapter numbers at their own lectures — so the panel does
the citing and he does the talking.

## → **https://epictetus-resurrected.vercel.app**

> **Status of the deliverables** — read this first, it is the honest version.
>
> | | |
> |---|---|
> | Corpus, index, retrieval, evaluation | **done and measured** |
> | Agent worker (speech, language model, voice, 3 tools, RAG) | **done, 50 tests pass** |
> | Web front end + token endpoint | **done, 18 tests pass, deployed** |
> | Worker container | **builds clean** — 1.39 GB, index asserted at build time |
> | Deployed link | **live** — front end on Vercel, token endpoint verified in production |
> | Hosted worker | **live** — LiveKit Cloud, US East, registered as `epictetus` |
> | Spoken call, end to end | **done** — see the transcript of the gate below |
> | Video | **not yet** |
>
> **A real spoken call has now been made through the deployed link** — thirteen
> turns over six minutes, no errors. Retrieval ran on every one of them, and
> **three cleared the 0.36 gate**:
>
> | turn | cosine | grounded on |
> |---|---|---|
> | *"...I'm chasing certainty, honestly"* | 0.379 | Book 2 Ch. 1, Book 1 Ch. 27 |
> | *"...things are uncertain, or difficult"* | 0.388 | Book 2 Ch. 5, Book 2 Ch. 1, Book 1 Ch. 28 |
> | *"...the opportunity cost, I'm losing time"* | 0.363 | Book 4 Ch. 3, 10, 12; Book 2 Ch. 10 |
>
> Three out of thirteen reads as far too strict until you look at the other ten.
> A real conversation is two or three questions with short replies hanging off
> them — *"feeling stuck"*, *"two weeks at most"* — and those are answers to
> something **he** just asked, with nothing of their own to retrieve against. The
> written question sets could never contain a turn of that shape. The full
> turn-by-turn reading, including two honest near-misses at 0.310 and 0.328, is
> in [`saved-results/first-live-call.md`](saved-results/first-live-call.md).
>
> **Also verified with the real keys:** the worker registers with LiveKit as
> `agent_name: epictetus`; the production token endpoint mints a token with a
> unique room, minimal grants and agent dispatch; a sentence spoken by ElevenLabs
> and fed back to Deepgram came back word for word at confidence 1.000; and the
> persona holds, with the tools firing, nothing cited out loud, and no philosophy
> at "hello".
>
> **What is still open:** the video is not recorded. Everything claimed with a
> number was measured; everything not run says so.

---

## What it looks like

```
  BROWSER (Vercel)                LIVEKIT CLOUD              AWS (agent worker)
 ┌────────────────────┐          ┌──────────────┐          ┌──────────────────────┐
 │ Next.js app        │          │              │          │ Python worker        │
 │                    │  WebRTC  │              │  WebRTC  │ (livekit-agents)     │
 │ [Start Call] ──────┼─────────>│  Room        │<─────────┤                      │
 │                    │  audio   │              │  audio   │  ┌────────────────┐  │
 │ live transcript    │<─────────┼──────────────┼─────────>│  │ STT  Deepgram  │  │
 │                    │  text    │              │          │  │ VAD  Silero    │  │
 │ ┌────────────────┐ │          │              │          │  │ LLM  gpt-4.1   │  │
 │ │ SOURCE PANEL   │ │<─────────┼── data ch ───┼──────────┤  │ TTS  11Labs    │  │
 │ │ Book II Ch. 5  │ │          │              │          │  └────────────────┘  │
 │ │ "..."          │ │          └──────────────┘          │          │           │
 │ └────────────────┘ │                 ^                  │          v           │
 │ [End Call]         │                 │                  │  RETRIEVAL runs on   │
 └────────┬───────────┘                 │                  │  EVERY turn — it is  │──> index
          │                             │                  │  NOT a tool          │   (in image,
          │  POST /api/token            │                  │          +           │    in repo)
          └─────────────────────────────┘                  │  ┌────────────────┐  │
             Vercel serverless function                    │  │ 3 TOOLS        │  │
             signs the JWT with the LiveKit                │  │ look_up_modern │──┼──> web
             API secret (server-side only)                 │  │ search_notion  │──┼──> Notion
                                                           │  │ write_journal  │──┼──> Notion
                                                           │  └────────────────┘  │
                                                           └──────────────────────┘
```

**In:** your voice. **Out:** his voice, a live transcript, and a visible list of
the passages behind each answer.

| Stage | Choice | Why |
|---|---|---|
| Speech to text | Deepgram `nova-3` | fast and streaming |
| Voice activity | Silero | runs inside the worker, no network hop |
| Language model | OpenAI `gpt-4.1`, temperature 0.75 | holds a character while using tools |
| Text to speech | ElevenLabs `eleven_turbo_v2_5` | character over raw speed, on their fastest tier to claw the latency back |
| Web search | Tavily | one key, no OAuth |

All four are swapped in one place, `agent/main.py`.

---

## The part that matters: retrieval

### The corpus is a PDF, on purpose

The brief asks for a PDF. Rather than find one of unknown provenance, this repo
builds its own and can prove it is faithful:

1. `corpus/build/fetch_wikisource.py` pulls the Long translation of the
   *Discourses* from Wikisource.
2. `corpus/build/typeset_pdf.py` typesets it into `corpus/discourses.pdf`.
3. `agent/retrieval/parse_pdf.py` reads that PDF back and checks the text
   survived the round trip.

**95 chapters, 4 books, 118,841 words.** Chunked into **539 pieces**, each
carrying its book, chapter, title and page. Committed to `index/`, 18 MB, so
nothing has to be rebuilt to run this.

### Retrieval is not a tool, and that is the main design decision

The obvious way to add RAG to an agent is to give it a `search_the_discourses`
tool and let the model decide when to call it. This does not do that. Retrieval
runs in `on_user_turn_completed`, on **every** turn, before the model produces
anything.

The reason is uncomfortable: **`gpt-4.1` already knows a great deal about
Epictetus.** Hand it a retrieval tool and it can skip the tool, answer from
memory, and sound completely right. The demo would look perfect and the graded
system would be doing nothing. Running retrieval unconditionally means the
passages are either in the prompt or provably were not, and there is no path
where the model quietly routes around the thing being assessed.

The cost is one embedding call per turn — about 20 tokens and roughly 250 ms,
overlapping with speech that is still arriving.

### Hybrid search, and proof it earns its keep

Two searches run over the same 539 chunks:

- **vector** — embeddings (`text-embedding-3-small`), finds meaning
- **keyword** — BM25, finds rare words and proper nouns

They are merged by **reciprocal rank fusion**: each list contributes
`1 / (60 + position)` for every chunk, and the contributions are added. Position
rather than score, because a cosine similarity and a BM25 score are on different
scales and adding them together means nothing. No reranking model — this is
arithmetic, so it costs nothing and adds no network call.

Then: no chapter may supply more than 2 chunks, and the top 4 go to the model.

**Does the hybrid actually beat either half?** Two question sets, because one of
them lies.

| | | in top 4 | MRR |
|---|---|---|---|
| **53 questions generated from the chapters** | hybrid | 96.2% | 0.912 |
| | vector only | 90.6% | 0.822 |
| | keyword only | **96.2%** | **0.921** |
| **12 written as a person would speak them** | hybrid | **75.0%** | 0.528 |
| | vector only | 66.7% | **0.583** |
| | keyword only | 41.7% | 0.201 |

The generated set was made by showing a model each chapter and asking for
questions naming the specific people and examples in it. That is what makes a
question answerable from exactly one chapter — and it also hands BM25 the exact
rare words it indexes on. **On that set keyword search alone beats the vector
side and matches the hybrid.** Read alone, it says the embeddings are a waste of
money.

The second set was written by hand, phrased the way someone actually talks —
*"how do I stop being angry at my coworker every time he messes something up"* —
with no proper nouns and no borrowed phrasing. **There, keyword search
collapses to 41.7%.** Someone describing a cancelled flight shares no rare words
with a 2nd-century Greek text.

Each half wins on one set. **The hybrid is the only setup that is never worst,
and it wins on the set that matches how people actually speak.** That is the
argument for paying for both, and it is not an argument I could have made from
the first set alone.

### The relevance gate, and the number that was wrong twice

He should not quote philosophy at *"hey, can you hear me?"*. So passages are only
used if the best vector match clears a similarity threshold; below it the turn
goes ungrounded and he answers from his own knowledge.

That threshold was set at **0.42** from the generated set, where small talk tops
out at 0.354 and the weakest real question scores 0.494 — an apparently clean gap.

**The hand-written set destroyed that.** Real spoken questions score from 0.19 to
0.50: they reach right down into where small talk lives. The clean gap was an
artifact of questions borrowing the chapters' vocabulary. At 0.42, six of twelve
real questions would have gone ungrounded.

It is now **0.36** — the highest value that still rejects every small-talk turn.
It grounds 61 of the 65 real questions across both sets. Headroom is about 0.006
in each direction, which is thin, and the honest reason to accept it is that both
failure modes are mild: ground a tool turn by mistake and the model gets passages
it ignores while it searches the notes; miss a real question and he answers from
his own knowledge, which for this particular character is not nothing.

An idea that did **not** work, recorded because it sounds right: gating on how
far the best chunk *stands out* from the rest, rather than its absolute score.
Small talk turns out to show a **larger** standout than real questions, because
its candidates are uniformly poor and the top one wins a weak field. Raw
similarity separates far better than any of the three variants tried.

Full numbers, distributions and reproduction:
**[`saved-results/retrieval-parameters.md`](saved-results/retrieval-parameters.md)**.

### What was deliberately not tuned

The rule was set before the first measurement: run once with sensible defaults,
and if they pass, stop. They passed at 96.2% on the first run, so the candidate
pool size, the number kept, and the per-chapter cap were never swept. Pushing
96.2% to 98% would be fitting the parameters to 53 questions I generated myself.

---

## Tools

The brief requires one. There are three, and retrieval is deliberately **not**
among them (see above).

| Tool | Does | Fits the story because |
|---|---|---|
| `look_up_modern_thing` | web search | he has been dead 1,900 years and nothing is familiar |
| `search_my_notion` | Notion search — free-text, then reads the page it found | he asks what you have written down when nobody was listening |
| `write_to_journal` | Notion write-back | Stoics ended the day writing down what they resolved |

All three return prose, not JSON, because the model is about to say the result out
loud. All three publish a line to the browser before they run, so a second of
silence reads as him doing something rather than as a broken call.

**Notes are searched, not read from a fixed page.** `search_my_notion` takes
whatever the conversation has turned to and calls Notion's `POST /v1/search`,
which needs no database id and reaches any page shared with the integration; a
second call reads that page's blocks. The write is the exception — it appends to
one pinned page id, because a bad title match on a *write* puts text somewhere
the caller did not expect, which is worse than a read that simply misses.

**Google Calendar was cut.** An earlier version had a fourth tool reading my
calendar. It was the most setup in the project (OAuth consent screens, redirect
URIs, a verification flow) for the least character: Epictetus asking what you
have *written down* is closer to the Stoic evening review than Epictetus reading
your meeting schedule. Cutting it removed the only OAuth here.

### The personal tools have two backends, and why one is behind a passphrase

My notes are useless to a grader, and pointing a public URL at my real account is
worse than useless. So each personal tool sits behind one interface with two
implementations:

- **demo** — seeded, plausible notes from a hard week (a performance review
  being rehearsed at 3am, a friend who only ever asks for favours, a parent's
  test results). This is what every visitor gets, and it is what the demo was
  always going to show.
- **live** — my real Notion.

**The switch is a passphrase, not a name.** The first design compared the
caller's display name to mine. That is not a credential: this project is
described in a public README and a public video, and the link stays up for two
weeks, so anyone who read either could type my name and read my real notes.

Instead the passphrase is entered on the start screen, sent to the Vercel token
endpoint, and compared **there** against an environment variable, in constant
time, hashed first so the comparison does not leak length. The verdict is written
into the participant's **signed** access token, which the worker reads and the
caller cannot forge. Demo is the default and every failure path — no passphrase,
wrong passphrase, missing credential, a page never shared with the integration,
API timeout mid-call — lands on demo. A grader never sees an error; they see
plausible notes.

It fails closed: if the server has no passphrase configured, the live backend is
unreachable rather than unlocked by an empty string. That is tested.

---

## Design decisions and assumptions

**Assumptions I made rather than asked about:**

1. **"Deploy on Vercel/AWS" vs "hosted locally or on AWS (bonus points)".** The
   brief says both. I went with AWS for the worker: it satisfies the strict
   sentence *and* collects the bonus, so it is the only reading that cannot lose
   points. The front end and token endpoint are on Vercel regardless.
2. **A grader will ask about a specific fact in a specific chapter.** That shaped
   the whole evaluation: the metric is "is the right chapter in the top 4".
3. **The Long translation is acceptable** as the *Discourses* — it is the standard
   public-domain English text.
4. **Latency budget favours character over speed.** ElevenLabs was chosen over
   faster options for voice fidelity, on their fastest model tier to recover some
   of it. If a live call turns out to feel slow, the fix is a faster ElevenLabs
   model, not a different vendor.

**Decisions worth naming:**

- **Retrieval on every turn, not as a tool** — the central one, argued above.
- **The gate reads raw similarity, not the fusion score.** The plan originally
  said to gate on the best fusion score. Fusion scores describe *rank*, not
  relevance: the top result scores about the same whether it is a perfect match
  or the least-bad of 500 irrelevant chunks, so gating on it would not gate
  anything. This is also why the fusion arithmetic is written out by hand instead
  of using LlamaIndex's `QueryFusionRetriever` — that discards the component
  scores, and the component scores are exactly what the gate needs.
- **A rule from the plan was dropped after measuring.** The plan called for
  skipping retrieval on turns that dispatch a tool call. It turns out the two
  highest-scoring small-talk turns *are* the tool turns, and the gate already
  rejects them — a second mechanism doing the first one's job. One mechanism.
- **He is addressed in the second person in the system prompt** — his situation,
  not a description of him. A model handed a character description tends to play
  a narrator describing that character; handed the character's own circumstances,
  it plays the character.
- **The index is committed.** 18 MB, and it means the numbers in `saved-results/`
  reproduce and a cold worker does not depend on someone else's CDN.

---

## Running it

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env      # then fill it in
```

The index is committed, so there is nothing to build. Then:

```bash
.venv/bin/python -m pytest tests -q
```

```bash
.venv/bin/python eval/run_retrieval_eval.py
```

```bash
.venv/bin/python eval/run_retrieval_eval.py --questions eval/spoken_questions.json
```

Talk to him in a terminal, no browser needed:

```bash
.venv/bin/python agent/main.py console
```

The web app:

```bash
cd web && npm install && npm test && npm run dev
```

To rebuild the corpus and index from scratch (about $0.003 of embeddings):

```bash
.venv/bin/python corpus/build/fetch_wikisource.py && .venv/bin/python corpus/build/typeset_pdf.py && .venv/bin/python -m agent.retrieval.search.index_store
```

---

## Deploying

**Front end and token endpoint → Vercel.** Point a Vercel project at this repo
with **Root Directory set to `web`**, and set `LIVEKIT_URL`, `LIVEKIT_API_KEY`,
`LIVEKIT_API_SECRET`, and optionally `LIVE_BACKEND_PASSPHRASE`. The API key and
secret must be server-side environment variables — anything prefixed
`NEXT_PUBLIC_` ships to the browser, and this secret can sign a token for any
room.

**Worker → anywhere that runs a container**, from the root `Dockerfile`. It is a
plain long-running process; it does not care where it runs, as long as it
*keeps* running.

```bash
docker build -t epictetus-worker .
```

The Dockerfile sits at the root rather than beside the rest of the deploy config
because LiveKit Cloud looks for it there — see below.

The image ships the index and pre-downloads the local voice-activity model, and
the build fails if the index is missing or incomplete — better a failed deploy
than a worker that registers as healthy and answers everything ungrounded. The
build prints `index loads: 539 chunks, 1536 dims`, and the finished image is
1.39 GB and runs as uid 10001, not root.

Two things this build taught, both recorded in the Dockerfile itself: the
stemmer under the BM25 index has no prebuilt wheel for `python:3.12-slim` and
has to be compiled, so a compiler is installed and removed inside one layer; and
the index check reads the index files directly rather than calling the real
loader, because the loader constructs an embedding model and would need an
OpenAI key — which has no business being in an image layer.

`deploy/worker/ecs-task-definition.json` is the Fargate side: one service with
one task, keys read from Secrets Manager rather than written into the task
definition, and no inbound ports, because the worker dials out to LiveKit and
nothing dials in. Fill in the account, region and secret ARNs, then:

```bash
aws ecs register-task-definition --cli-input-json file://deploy/worker/ecs-task-definition.json
```

One trap worth naming: the task definition's `cpuArchitecture` has to match the
machine that built the image. Built on an Apple Silicon Mac it is `ARM64`, and a
mismatch shows up as the container exiting instantly with an exec format error.

**Why not serverless:** a LiveKit agent holds a WebRTC connection for the length
of a call and registers with LiveKit to wait for dispatch. Per-request serverless
cannot do that. If the worker is off, the link is dead.

**The short path: LiveKit Cloud agent hosting.** One command from the repo root:

```bash
set -a && . ./.env && set +a && lk agent create --secrets-file .env .
```

`--secrets-file .env` uploads the API keys to LiveKit so the hosted worker has
them; that upload is the reason this command is left for a human to run rather
than run from an agent session. Afterwards, `lk agent deploy .` pushes a new
version and `lk agent list` shows it — the dispatch name should read
`epictetus`, which is the name the token asks for.

**Three things this cost an hour, all worth knowing before you start:**

1. **LiveKit builds the image; you cannot hand it one you built.** `--image` and
   `--image-tar` exist but return `PERMISSION_DENIED: Bring Your Own Container is
   only available for Enterprise projects`. So LiveKit needs a `Dockerfile` in the
   directory you point it at, which is why ours is at the repo root.
2. **The free plan allows exactly one hosted agent.** A second `create` fails
   with a max-agents error. If the slot is already taken by something made in
   LiveKit's web builder, the CLI cannot remove it — `lk agent delete` answers
   `This action isn't available for Builder agents` and you have to do it from
   the dashboard.
3. **`create` writes `livekit.toml` with the agent id, and it must be committed.**
   Without it the next `deploy` has nothing to update and makes a second agent —
   which, per (2), fails.

Cost: LiveKit's free Build plan includes 1,000 agent session minutes a month, and
it bills session minutes rather than idle hosting, so a deployed worker sitting
between calls costs nothing.

**Fallback order if that fights back**, decided in advance rather than at 2am:
LiveKit Cloud → AWS Fargate (above) → any host that runs a long-lived container.

---

## Limitations

1. **The free LiveKit plan allows one hosted worker and 1,000 session minutes a
   month.** That is roughly two hundred five-minute calls, which is plenty for a
   review and nothing like production. There is one replica in one region, so a
   restart is a few seconds of dead link.
2. **"my flight got cancelled and I lost the whole day"** scores 0.19 and goes
   ungrounded — far below every other real question. Modern concrete nouns with no
   abstract vocabulary are the worst case here, and no threshold that also
   rejects small talk would catch it.
3. **12 hand-written questions is a small sample**, and their gold labels are my
   own judgement — several could fairly be answered from more than one chapter.
   The comparison between configurations is sound because the same labels apply
   to all three; a single percentage from that set should not be quoted alone.
4. **The generated set flatters the system.** 96.2% should always be read next to
   75.0%.
5. **The relevance gate has ~0.006 of headroom.** A different corpus or embedding
   model would need it re-measured, not copied.

---

## AI tools used

Built with **Claude Code** (Opus 5) doing essentially all of the typing, under my
direction. Worth naming specifically, since the brief asks:

- **Where it was most useful:** the retrieval evaluation harness. Asking for a
  second, adversarial question set — one written to *defeat* keyword search — is
  what exposed both the BM25 bias in the first set and the wrong gate threshold.
- **Where it was wrong and I caught it:** it produced a `2022-06-28` Notion API
  version from memory; the current one is `2026-03-11`, found by looking up the
  live docs. It also reported a keyword-only score of 0.0%, which was a bug in the
  measurement (the gate was zeroing the very scores being compared), not a finding
   — the corrected number is 96.2%.
- **`gpt-4.1`** generated the 53-question evaluation set from the chapters.
- **`text-embedding-3-small`** builds the index.
- The 12 spoken questions were written by hand, deliberately, because a model
  shown a chapter cannot help borrowing its words — which is the exact bias being
  tested for.

---

## Repo map

```
agent/           the worker
  main.py          pipeline: speech, model, voice, and the session
  persona/         who he is, and the three tools
  grounding/       the per-turn retrieval hook
  retrieval/       PDF parsing, chunking, hybrid search, the gate
  tools/           web search; personal tools with demo and live backends
corpus/          the Discourses: fetch it, typeset it, and the PDF itself
index/           the committed vector store and keyword index
eval/            the retrieval harness and both question sets
web/             Next.js front end and the token endpoint
deploy/worker/   Dockerfile for the agent worker
saved-results/   measurements, with the reasoning that used them
planning/        the plan this was built from
tests/           agent behaviour tests
```
