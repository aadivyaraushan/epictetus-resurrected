# Epictetus, Resurrected — Plan

**Bluejay take-home: RAG-enabled LiveKit voice agent**
Written 2026-07-30 · Deadline **Fri 2026-07-31 23:59 PT** (~32h from writing, ~20h of working time)

---

## 1. What we're building, in one breath

A voice call with Epictetus — the actual Stoic, pulled into 2026 — who gives you
counsel on how to live, grounded in his own *Discourses*. He asks you questions
when he doesn't have context. He can look up modern things he's never heard of,
read your calendar and notes to know what's actually going on in your life, and
write down what you resolved at the end of the call.

The personal problem: I want the Stoics' actual advice on how to live, in
conversation, instead of digging through a 450-page book.

---

## 2. System, end to end

```
  BROWSER (Vercel)                LIVEKIT CLOUD              AWS (agent worker)
 ┌────────────────────┐          ┌──────────────┐          ┌──────────────────────┐
 │ React app          │          │              │          │ Python worker        │
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
 └────────┬───────────┘                 │                  │  EVERY turn — it is  │
          │                             │                  │  NOT a tool (see §3) │──> index
          │  POST /api/token            │                  │          +           │   (in image,
          └─────────────────────────────┘                  │  ┌────────────────┐  │    in repo)
             Vercel serverless fn                          │  │ 4 TOOLS        │  │
             mints JWT w/ LiveKit                          │  │ look_up_modern │──┼──> web
             API key+secret (server-side only)             │  │ read_calendar  │──┼──> GCal
                                                           │  │ read_notes     │──┼──> Notion
                                                           │  │ write_journal  │──┼──> Notion
                                                           │  └────────────────┘  │
                                                           └──────────────────────┘
```

**Inputs:** user's voice; the *Discourses* (fixed, pre-indexed); optionally the
user's calendar + Notion.
**Outputs:** Epictetus's voice; a live transcript; a visible source panel naming
the book + chapter behind each answer; a journal entry written back to Notion.

**The pipeline, named** (the brief asks for "configurable STT, LLM, TTS, VAD" —
all four are swappable plugin choices in LiveKit's `AgentSession`, set in one
place):

| Stage | Choice | Why |
|---|---|---|
| STT | **Deepgram Nova** | fast, streaming, free credit covers this |
| VAD | **Silero** | runs locally in the worker, no network hop |
| LLM | **OpenAI `gpt-4.1`** | good instruction-following for a persona that has to stay in character while using tools |
| TTS | **ElevenLabs**, fastest model tier | character fidelity — see §5 |
| Web search | **Tavily** | one API key, no OAuth, built for LLM use — signup is minutes, which matters since this is on the required path |

---

## 3. RAG — the part that gets graded hardest

The brief says: *"I will ask about a specific fact in a specific chapter, so a
proper RAG setup is essential."* Everything below is aimed at that sentence.

### Corpus — and why it's a PDF

The brief says "PDF" six times: *"retrieve information from a large PDF"*, *"run
RAG over the content of the PDF"*. So the pipeline starts at a PDF, full stop.

I already have the *Discourses* as 94 clean chapter text files (fetched from
Wikisource, George Long translation — measured below). The two obvious ways to
get a PDF were:

1. **archive.org's scanned Long translation** — rejected. ~35% of its words score
   under 30% OCR confidence. Bad OCR means confidently wrong answers on exactly
   the fact-in-a-chapter question the grader will ask.
2. **Typeset a clean PDF from the verified text** — chosen. One book, one
   chapter per section, real page structure, committed to the repo.

Then the pipeline **parses that PDF back out** with a normal PDF reader — the
same code path a user's uploaded PDF would take. Nothing reads the .txt files at
runtime.

This is a deliberate trade and it goes in the README: I gave up "found a PDF in
the wild" in exchange for a corpus whose every word is verifiable against
Wikisource. Building the PDF from trusted text and parsing it back is *more*
honest than shipping OCR noise and calling it a document.

| | |
|---|---|
| Text | *Discourses*, George Long translation, Wikisource |
| Coverage | **94 / 94 chapters**, all non-empty |
| Size | **125,425 words ≈ 167k tokens** |
| Chapter length | min 149 · median 1,125 · mean 1,334 · p90 2,210 · max 9,271 words |
| Over 3,000 words | only 3 chapters (B4C1, B3C24, B3C22) |

167k tokens will not fit in a voice agent's context, and stuffing it would blow
latency even if it did. **Retrieval is genuinely load-bearing here** — that's the
honest answer for the "RAG trade-offs" section of the video.

### The stack, named

The brief asks for "vector DB choice, chunking strategy, frameworks" in writing,
so nothing here stays vague:

| Piece | Choice | Why |
|---|---|---|
| Framework | **LlamaIndex** | brief names it; hybrid retrieval is built in |
| PDF parse | **pypdf** | plain, no service |
| Embeddings | **OpenAI `text-embedding-3-small`** | cheap (~$0.01 for 500 chunks), good enough at this scale |
| Vector store | **LlamaIndex `SimpleVectorStore`, persisted to disk** | ~500 chunks does not need a database. Committed to the repo, loaded into memory at worker start, no network hop, nothing to keep alive or pay for |
| Keyword | **`BM25Retriever`** over the same docstore | |
| Fusion | **`QueryFusionRetriever`, `mode="reciprocal_rerank"`, `num_queries=1`** | merges the two rankings **with no reranker model** — no Cohere bill, no extra latency. `num_queries=1` disables LlamaIndex's query-generation step, which would add an LLM round-trip mid-call |

That last row is why there's no reranker line in the money table: reciprocal rank
fusion is arithmetic on the two result lists, not a model call.

### Pipeline

```
 BUILD ONCE (committed to repo)         RUNTIME PARSE            chunking
 ┌──────────────┐    ┌───────────┐    ┌──────────────┐   ┌────────────────────┐
 │ 94 verified  │    │ discourses│    │ pypdf reads  │   │ ~400 tokens        │
 │ chapter .txt │───>│  .pdf     │───>│ it back out; │──>│ ~60 overlap        │
 │ (Wikisource) │    │ (typeset, │    │ chapter      │   │ NEVER cross a      │
 └──────────────┘    │  chaptered│    │ headings     │   │ chapter boundary   │
   build-time only   └───────────┘    │ → structure  │   └─────────┬──────────┘
                       ^              └──────────────┘             │
                       │                     ^                     │
              THE deliverable PDF     same code path a user's      │
                                      uploaded PDF would take      │
                                                                   v
      query time                                            ┌──────────────┐
 ┌──────────────────────┐                                   │ vector       │
 │ user question        │                                   │   +          │
 │   │                  │                                   │ BM25         │
 │   v                  │<──────────────────────────────────│ (hybrid)     │
 │ retrieve 12          │                                   └──────────────┘
 │   │                  │                                     ≈ 500 chunks
 │   v                  │                                     each carries
 │ rerank               │                                     {book, chapter,
 │   │                  │                                      chunk_ix, page}
 │   v                  │
 │ keep top 3-4         │
 │   │                  │
 │   v                  │
 │ into the LLM prompt  │
 │ + out the data chan  │
 └──────────────────────┘
```

**Round-trip check before anything else is built:** parse the generated PDF,
confirm all 94 chapters come back out with correct book/chapter labels and no
mangled text. If typesetting corrupts anything, that's known in minute five, not
after the index is built. This is the first thing that runs.

**Why each number:**

- **~400-token chunks.** A median chapter is ~1,500 tokens, so a chapter becomes
  3–4 chunks. Small enough that a retrieved chunk is *about* one thing; big
  enough to carry a complete argument, which matters because Epictetus makes his
  point across a few sentences, not in one line.
- **~60-token overlap.** Keeps a thought that straddles a boundary findable from
  either side.
- **Chapter boundaries are hard walls.** A chunk spanning two chapters would get
  cited to the wrong chapter — and the grader is testing exactly that.
- **Hybrid (vector + BM25).** Vector search alone misses proper nouns and rare
  words; a question naming a person or an unusual term should hit the lexical
  side. The graded question is a *specific fact*, which is where lexical wins.
- **Retrieve 12 → rerank → keep 3–4.** Wide first pass so the right chunk is in
  the pool; rerank because voice can only afford 3–4 chunks of prompt before the
  first-token delay is audible.
- **Index built once, committed to the repo, baked into the worker image.** The
  brief lists "Vector store" as a deliverable, so the built index files live in
  git — not only inside an ephemeral Docker layer. No vector-DB network hop on
  the hot path, no separate service to keep alive, nothing to pay for after
  submission. The corpus never changes, so there's no reason to make it dynamic.
  A build script regenerates it from the PDF so it's reproducible, not a blob.

### Retrieval is not optional — it runs on every turn

This is the single most important decision in the plan.

LiveKit gives you two ways to wire RAG (confirmed in their external-data docs):

```
 A) RAG as a function tool          B) RAG in on_user_turn_completed
 ┌───────────────────────────┐      ┌───────────────────────────────┐
 │ user speaks               │      │ user speaks                   │
 │   │                       │      │   │                           │
 │   v                       │      │   v                           │
 │ LLM DECIDES whether to    │      │ hook fires — ALWAYS —          │
 │ search  ◄── may skip it!  │      │ retrieves, appends passages   │
 │   │                       │      │ to the chat context           │
 │   v                       │      │   │                           │
 │ extra round-trip          │      │   v                           │
 │   │                       │      │ ONE LLM call, already grounded │
 │   v                       │      └───────────────────────────────┘
 │ answer                    │
 └───────────────────────────┘
```

**Going with B.** The grader is going to ask a specific fact from a specific
chapter. With (A), a model that already knows Epictetus can decide it doesn't
need to look anything up, answer from memory, and be *right* — and the whole RAG
system sat there unused during the one moment it was being graded. That's not a
hypothetical; it's the predictable behaviour of an LLM that knows the material.

With (B) the retrieval is not a decision. It happens, the passages are in
context, and the source panel has something real to show. LiveKit also flags (B)
as the faster of the two — it skips the tool round-trip — which matters on a
voice call.

**"Always" needs a relevance gate, or he becomes a fortune cookie.** If passages
get appended on literally every turn, then "what's on my calendar tomorrow?" and
"hey, can you hear me?" both get Stoic philosophy stapled to them, and Epictetus
starts quoting himself at nothing. The brief grades personality and storytelling
explicitly — *"I will consider the creativity / story-telling to be your
behavioral"* — so this is not a cosmetic problem.

Gate: **drop the retrieved passages when the best fusion score is below a
threshold, and skip retrieval entirely on turns that dispatch a tool call.** The
threshold gets set from the eval harness — I already have scores for questions
with known-correct answers, so I can see where real hits sit versus noise. The
gate never blocks a genuine fact question; it stops him philosophising at
"hello."

**Validated live, not just offline.** The offline eval harness proves the right
chapter is *findable*. It cannot prove the pipeline fired during a real call. So
the integration checkpoint (§6) includes a spoken fact-from-a-chapter question,
and I check that the source panel names the right chapter — the grader's exact
test, run by me first — plus a chit-chat turn to confirm the gate holds.

**This doesn't cost us the brief's tool-call requirement.** The brief wants "a
tool call of your choice that fits in with the narrative" — that's the four
tools in §4, which are the narrative ones anyway. Retrieval moving out of the
tool list makes the tool calls *more* clearly in-story, not fewer.

### Citation

**Book + chapter only.** No chapter title. No self-quoting — Epictetus wouldn't
say "as I wrote in Book II." He speaks; the *panel* cites. The retrieved passage
and its book/chapter appear in the transcript sidebar.

That panel is doing real work: GPT already knows Epictetus, so a good spoken
answer alone doesn't prove retrieval happened. Showing the passage is what makes
the RAG visibly real to a grader.

### Retrieval evaluation (the fast loop)

Before any voice is involved:

```
 corpus (labeled by chapter)
        │
        v
 auto-generate ~60 questions, each with a known correct chapter
        │
        v
 run against the SAVED index, no LLM, no voice  ── seconds per run ──┐
        │                                                            │
        v                                                            │
 hit-rate: is the right chapter in top-k?  ──> tune params ──────────┘
```

One iteration is seconds because it touches nothing but the index. Params to
tune: chunk size, overlap, k, hybrid weighting. Target: right chapter in top-4
on the large majority of questions. **Chosen params get recorded in
`saved-results/` with the numbers that justified them** — that's the video's
"RAG trade-offs" segment, with evidence instead of assertion.

---

## 4. Tools (the brief requires ≥1; we ship 4)

Retrieval is **not** in this list — it runs on every turn, see §3. These are the
narrative tools, the thing the brief actually asks for.

| Tool | What it does | Fits the story because |
|---|---|---|
| `look_up_modern_thing` | web search | he's been dead 1,900 years and everything is unfamiliar |
| `read_my_calendar` | Google Calendar | he asks what's actually on your plate |
| `search_my_notion` | Notion search — free-text query across whatever I've shared with the integration, then reads the matching page | the same, for what you've written down |
| `write_to_journal` | Notion write-back | Stoics ended the day writing down what they resolved |

**Notes are searched, not queried against a fixed database.** The first draft
named two Notion database ids, which meant deciding up front which notes
Epictetus was allowed to see. Instead `search_my_notion` takes whatever he wants
to look for — `POST /v1/search` needs no database id and returns any page shared
with the integration — and a second call reads that page's blocks. He asks "have
you written anything about this?" and goes and looks, which is both closer to
the character and less setup.

**Reads search; the write is pinned.** `write_to_journal` appends to one page id
held in an env var (`PATCH /v1/blocks/{page_id}/children`, a normal page, not a
database). Searching for the write target by title would mean a bad match writes
into the wrong page, and a write that lands somewhere unexpected is worse than a
read that misses.

**What this needs from the user:** Notion's search only sees pages explicitly
shared with the integration, so the scope is set in Notion's UI, not in code —
which also makes it the natural privacy control.

**Grader problem:** the grader isn't me. My calendar and Notion return nothing
for them, and I'd be handing a company a public URL wired to my real accounts.

**Answer, designed in rather than bolted on:** each personal tool sits behind one
interface with two backends — live (my credentials, my session) and a seeded
demo backend (a plausible fictional week) that everyone else gets. The agent
can't tell which it's talking to.

**How it switches — and this has to be a secret, not a name.** My first instinct
was "check the participant's name against mine." That's unsafe: the design gets
described in a public README and a public video, so anyone who knows my name
could type it into a link that stays live for 14 days and read my real calendar
and notes. Guessable is not a credential.

So: **the live backend is unlocked by a passphrase**, entered on the start screen
and compared server-side against an env var. No passphrase, wrong passphrase,
missing credential, or a failed API call → **demo backend**. Demo is the default
and the fallback, so a revoked token or an expired OAuth grant degrades to a
working demo instead of a dead tool mid-call. The grader never sees an error;
they see Epictetus reading a plausible week. I reach the live path on the same
deployed link everyone else uses, so there's no separate build and no local-only
path that goes untested.

**Standing option if this still feels like too much exposure:** ship the public
deployment demo-only and never wire the real accounts to it at all. That costs
nothing that's graded — the grader was always going to see the demo backend.

**Scope note:** the brief requires *one* tool call. Four is my own choice, made
knowing the schedule is tight. Web search sits **above** the cut line so the
requirement survives every cut path; the other three are where the schedule
buffer actually lives (§6).

---

## 5. Persona

Epictetus, a lame former slave who taught in Nicopolis, now in 2026. Blunt,
warm, Socratic. Asks a lot of questions when he lacks context — that's both
in character and the thing that makes the calendar/notes tools fire naturally.

ElevenLabs TTS, chosen over lower-latency options for character fidelity, on
ElevenLabs' fastest model tier to claw the latency back. Latency budget lives or
dies on this choice; if the round-trip is bad, the fallback is a faster
ElevenLabs model, not a different vendor.

**Persona gets a check too, because it's graded.** The brief is unusually direct
about this — *"Put time into this part! I will consider the creativity /
story-telling to be your behavioral!"* — and it would be a strange plan that
measures retrieval to two decimal places and leaves the graded personality to
vibes. At the integration checkpoint (§6) I run one scripted call and check four
things:

1. **In character** — does he sound like a blunt Greek teacher, or like an
   assistant wearing a toga?
2. **Asks questions** — when I give him a vague problem, does he ask what's
   actually going on before advising? (This is the behaviour I asked for, and
   it's what makes the tools fire naturally.)
3. **No self-quoting** — he never says "as I wrote in Book II." The panel cites;
   he speaks.
4. **Doesn't philosophise at "hello"** — the relevance gate (§3) holds on small
   talk.

Any of the four failing is a system-prompt fix, which is minutes, not hours —
but only if I've actually listened to a call before recording the video.

---

## 6. Schedule — required work first, optional work *is* the buffer

```
 REQUIRED PATH — 17.0h                                    cumulative
 ├─ 0.5h  build PDF, parse it back, verify 94 chapters      0.5   ◄── fails fast
 ├─ 2.0h  chunk → index → eval harness                      2.5       no keys needed
 ├─ 1.0h  DEPLOY SPIKE: stub agent → AWS,                   3.5   ◄── proves the
 │        token endpoint → Vercel, join a real room                   riskiest path
 ├─ 3.0h  LiveKit agent: room join, STT/LLM/TTS/VAD         6.5       on day one
 ├─ 2.0h  RAG tool + persona + ElevenLabs voice             8.5
 ├─ 1.0h  retrieval tuning against the eval harness         9.5
 ├─ 1.0h  INTEGRATION CHECKPOINT: full local call,          10.5  ◄── first real
 │        voice in → cited answer out → transcript;                  end-to-end run
 │        persona check (§5), gate holds on small talk,
 │        and TIME the turn — retrieval now runs before
 │        every LLM call, so its cost is in the loop
 ├─ 3.0h  React frontend: start/end, transcript, sources    13.5      is HERE, not
 ├─ 2.0h  full deploy (de-risked by the spike)              15.5      in the video
 ├─ 0.5h  web search tool  ◄── THE required tool call            16.0
 ├─ 0.5h  SMOKE TEST THE SUBMITTED LINK: fresh browser,         16.5
 │        incognito, not my machine — full call, spoken
 │        fact-from-a-chapter question, panel cites right
 │        chapter, a tool call fires, end call cleanly
 ├─ 0.5h  video outline written while it's all fresh            17.0
 │
 │        ── at this point the submission is COMPLETE and passing ──
 │
 OPTIONAL — 3.5h, cut from the bottom up
 ├─ 0.5h  journal write-back                                    17.5  ◄── cut 3rd
 ├─ 1.0h  Notion read (incl. its demo backend)                  18.5  ◄── cut 2nd
 ├─ 2.0h  Google Calendar OAuth (incl. its demo backend)        20.5  ◄── cut 1st
 │
 WRITE-UP — 3.0h, never cut
 ├─ 1.5h  README + design document
 └─ 1.5h  YouTube video, from the hour-17 outline
                                              TOTAL 23.5h vs ~20h available
```

**Web search is on the required path, and that's the whole reason it moved.**
The brief's tool-call requirement is not a bonus — *"In the call, make a tool
call of your choice"* — so a cut path that removes every tool would fail an
explicit requirement. Web search is the cheapest of the four (no OAuth, no
account, no demo backend needed — a search API works the same for everyone), so
it's the one that belongs above the cut line. **Every cut scenario now still
ships at least one working, in-story tool call.**

**The video outline is written at hour 17, not hour 22.** Five minutes covering
four mandated topics is a tight edit, and drafting it cold at the end of a
20-hour sprint is how a required topic gets dropped. Half an hour while the
system is fresh in mind buys back more than it costs.

**The arithmetic doesn't close, and that's the point.** 23.5h against ~20h means
Calendar (2h) gets cut and I land at 21.5h; cut Notion read too and it's 20.5h.
The optional tools aren't a stretch goal — they *are* the buffer, spent only if
the required path came in under estimate. **If the required path itself overruns,
all three optional tools go and the submission still passes at 20h** — with the
web search tool, because that one is above the cut line.

**Honest read on slack: there is about an hour of it, and that's thin.** The
required path plus the never-cut write-up is 20h against ~20h available. That's
survivable only because the three biggest unknowns each have a written abort
rule (deploy spike §7, retrieval tuning below, host fallback §7) rather than an
open-ended "keep going until it works." **Nothing can start until the API keys
land** (§11) — if those arrive late, real available time is smaller than 20h and
Calendar and Notion go immediately rather than eventually.

**The 2am scenario, decided now while I'm rested.** If it's hour 18 and the full
deploy still isn't working, I do not keep debugging into the deadline. I ship, in
this order of preference:

1. **Worker on LiveKit Cloud, frontend on Vercel** — the §7 fallback. Still a
   public working link. Costs the AWS bonus point, nothing else.
2. **Worker anywhere that runs, frontend on Vercel** — any container host.
3. **Frontend on Vercel + a recorded call in the video, README stating plainly
   that the worker is not deployed and exactly why.** This loses real points and
   is the genuinely bad outcome — but an honest README plus a working video beats
   a dead link and silence, and it's still a submission.

Whichever branch I'm on, the README says so explicitly. **No branch involves
missing the deadline**; the deadline is fixed and the scope is what moves.

**Retrieval tuning gets the same discipline as the deploy spike.** Timebox: one
hour. If the eval harness shows the right chapter in the top 4 on most questions
at the *default* parameters, tuning is already done — stop and move on, don't
gold-plate the thing that's already passing. If it's still bad after an hour, ship
the best configuration measured so far and write the shortfall into the README's
trade-offs section, which is a graded section anyway. Tuning does not get to run
long; it is measurement, and measurement has diminishing returns.

**Two things moved earlier and they're the whole reason this schedule is
different from the last one:**

- **Deploy spike at hour 3.** Not the full deploy — a stub agent that says one
  sentence, running on AWS, joined from a Vercel-hosted page. LiveKit workers are
  long-running processes that register with LiveKit and wait for dispatch, which
  is not a shape AWS makes obvious. Finding that out at hour 3 leaves 17 hours to
  react. Finding it out at hour 15 ends the submission.
- **Integration checkpoint at hour 10.5.** The failure mode this kills: recording
  the video *as* the first full end-to-end run. One complete call — voice in,
  cited answer out, transcript rendering — before the frontend is polished.

**Cut order:** Google Calendar → Notion read → journal write-back → web search.
All four sit behind the same tool interface, so cutting one deletes a
registration, not a refactor. Never cut: README or video (both are graded
deliverables).

---

## 7. Hosting — reading the brief, and staying alive for the grader

**The brief says two different things.** Overview: *"You must deploy your Agent
on Vercel/AWS instead of running it locally."* Technical Requirements §1: *"The
LiveKit agent can either be hosted locally or on AWS (bonus points for AWS)."*

**Reading I'm going with:** AWS for the worker. It satisfies the strict sentence
and collects the bonus, so it's the only reading that can't lose points.
**I'll state this interpretation in the README** rather than hoping the grader
reads it the same way.

**Fallback if AWS fights back:** the frontend and token endpoint are on Vercel
regardless, so a worker that won't deploy to AWS is a *worker* problem, not a
project problem. The worker is a plain Python process in a container; it does not
care where it runs. Order: AWS → LiveKit Cloud's own agent hosting (one CLI
command against the same Dockerfile) → any container host that runs a long-lived
process.

**The spike is timeboxed and the abort rule is written down now, not decided at
2am:** the hour-3 spike gets **one hour**. If a stub agent isn't answering on AWS
by the end of it, I deploy to LiveKit Cloud hosting instead — that same hour —
and AWS becomes a leftover-time bonus attempt. Known failure modes to watch for
in that hour: worker registration hanging, and job dispatch taking tens of
seconds. Both are reported against `livekit/agents` and both look like "nothing
happens," which is exactly the kind of thing that eats an evening if there's no
rule to stop.

**Keep-alive policy — this is a deliverable, not an afterthought.** A LiveKit
agent worker is a long-running process that registers with LiveKit and waits to
be dispatched. It is not per-call serverless. If it's off, the link is dead, and
"a link to a fully deployed agent for the team to test" is the deliverable most
likely to be clicked days after submission.

> **Committed policy: the worker stays up for 14 days after submission.**
> A billing alarm fires at **$25**. The teardown checklist goes in
> `saved-results/` on day one with a calendar reminder, not written from memory
> two weeks later. If the alarm fires before day 14, I get told and decide —
> the worker is not silently killed.

The README will say the link is live through that window and give a contact for
a restart after it.

---

## 8. Money — needs explicit approval before first use

Everything below is on **personal accounts**; keys to be supplied by the user.
**I will state the literal account each key resolves to and get an OK before
first use.**

| Service | Estimate | Notes |
|---|---|---|
| ElevenLabs | $5–22 | biggest line; depends on tier |
| LLM (OpenAI) | $5–15 | |
| AWS (worker) | $10–20 | small always-on container, **14 days** per §7 — not the ~1 day I first assumed |
| Deepgram STT | ~$0 | free credit |
| Embeddings | <$0.10 | one-time build (~500 chunks) + one small call per turn |
| Tavily (web search) | $0 | free tier is far more than a demo needs |
| Reranker | $0 | none — reciprocal rank fusion is arithmetic, not a model (§3) |
| LiveKit Cloud, Vercel | $0 | free tiers |
| **Total** | **~$25–70** | rough, to be verified against live pricing |

**Teardown is scheduled, not remembered:** AWS worker + any ElevenLabs
subscription get a written checklist in `saved-results/` on day one, with the
$25 billing alarm as the backstop. See §7 for the 14-day window.

---

## 9. Deliverables checklist (straight from the brief)

- [ ] Single Git repo
- [ ] Vercel deployment link, working for someone who isn't me
- [ ] LiveKit Python backend incl. RAG logic
- [ ] React frontend: Start Call, live transcript, End Call
- [ ] **The PDF itself, committed to the repo**
- [ ] Vector store committed to the repo (not only inside the image)
- [ ] README with design doc: end-to-end, how RAG was integrated, tools/frameworks, setup
- [ ] Design Decisions / Assumptions: trade-offs, hosting, RAG (vector DB, chunking, frameworks), LiveKit agent design
- [ ] **AI tools used, documented** — the brief's Constraints line: *"Use any AI tools you need/want, just document them."* Includes Claude Code, which wrote much of this
- [ ] YouTube ≤5 min covering: **room token generation · tool calls · RAG setup · RAG trade-offs**

---

## 10. Known risks

| Risk | Why it bites | What we do |
|---|---|---|
| Deployment eats the schedule | LiveKit worker on AWS is the least-rehearsed step | **deploy spike is a scheduled line item at hour 3** (§6), not an intention; host fallbacks named in §7 |
| Worker is off when the grader clicks | it's a long-running process, not per-call serverless | 14-day keep-alive committed in §7, billing alarm at $25 |
| Typesetting the PDF corrupts the text | everything downstream inherits it | parse-back check is the **first** task, before the index exists |
| Voice round-trip too slow | ElevenLabs chosen for character, not speed; **and** per-turn retrieval now sits inside the response loop, embedding call included | timed at the integration checkpoint (§6); levers in order: fewer chunks (3, not 4), faster ElevenLabs model, cache embeddings for repeated turns |
| GPT answers from memory, not retrieval | Epictetus is famous enough that the LLM can answer correctly without looking | retrieval runs on every turn, not by LLM choice (§3); offline harness proves findability, integration checkpoint + link smoke test prove it fires live |
| LiveKit Cloud hosting used instead of AWS | costs the AWS bonus point | only after the timeboxed spike fails (§7); a working link beats a bonus point |
| Public link exposes my real calendar/notes | link stays live 14 days and the design is public | live backend gated on a passphrase, not a guessable name (§4); demo-only deployment is a standing option |
| Everything optional gets cut → no tool call | tool call is a hard requirement, not a bonus | web search moved **above** the cut line (§6) |
| Epictetus quotes scripture at "hello" | per-turn retrieval with no gate hurts the graded personality | score threshold + skip on tool-call turns (§3), checked at the integration checkpoint |
| Google OAuth rabbit hole | consent screens, verification, redirect URIs | last in order, first to cut |
| The 3 giant chapters (up to 9,271 words) | ~23 chunks from one chapter can crowd out the pool | watched in the eval harness; per-chapter cap on retrieved chunks if it shows up |

---

## 11. Open, needs the user — **these block the clock**

Only the first task (build the PDF, parse it back, verify 94 chapters) can run
without these. Everything after hour 0.5 waits.

1. **Git.** The project directory is empty and not a repo. Per your rules I
   won't `git init` on my own — say the word and I will.
2. **API keys, in the order they're needed:**
   | When | Keys |
   |---|---|
   | hour 0.5 | OpenAI (embeddings — the index can't be built without it) |
   | hour 2.5 | LiveKit Cloud, AWS |
   | hour 3.5 | Deepgram, ElevenLabs |
   | hour 16 | Tavily (web search) |
   | optional | Notion, Google |

   Account confirmation happens per key, before first use — I'll name the literal
   account each one resolves to and wait for your OK. All are personal accounts
   per your earlier note.
3. **How exposed do you want the deployed link to be?** Passphrase-gated live
   backend (§4) or demo-only. Demo-only costs nothing that's graded. My default
   if you don't weigh in: passphrase.
