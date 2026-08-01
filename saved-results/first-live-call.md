# The first real spoken call — what the relevance gate did on live speech

> **Historical result:** this call supported the former `0.36` gate. A later
> conversation exposed required turns below it; the replacement is documented
> in [`rag-luna-filter-2026-07-31.md`](rag-luna-filter-2026-07-31.md).

**Date:** 2026-07-31, 06:26–06:32 local
**What this is for:** every number in `retrieval-parameters.md` was measured against
written questions. This is the first time the gate met a person talking. It is the
evidence for the "RAG trade-offs" segment of the video, and the thing to re-read before
anyone moves `MIN_COSINE_TO_GROUND`.
**Who should read it:** anyone about to change the gate, and anyone who wants to know
whether the design survives contact with a real conversation.

**A note on the transcript.** The turns below are paraphrased, not quoted. The call was
a real conversation about the caller's own work, and this file is committed to a repo
that gets submitted. The scores, the timings and the chapters are exact; the wording is
loosened just enough not to publish someone's evening.

---

## What happened

Room `epictetus-c571c988`, caller `caller-5a50bc54`, worker on a laptop, demo backend
for the personal tools. **Thirteen turns over six minutes. No errors, no dropped audio,
no crash.** Retrieval ran on all thirteen — that is the design, and it held.

**Three turns were grounded. Ten were not.**

| # | turn (paraphrased) | cosine | verdict |
|---|---|---|---|
| 1 | wanting more clarity in life | 0.318 | — |
| 2 | correcting that: it is really chasing *certainty* | **0.379** | **Book 2 Ch. 1, Book 1 Ch. 27** |
| 3 | about things being uncertain and difficult | **0.388** | **Book 2 Ch. 5, Book 2 Ch. 1, Book 1 Ch. 28** |
| 4 | their research is not going well | 0.227 | — |
| 5 | it has dragged on too long | 0.255 | — |
| 6 | it is not going as hoped; what "done" would mean | 0.310 | — |
| 7 | the real cost is the time lost to other things | **0.363** | **Book 4 Ch. 3, 10, 12; Book 2 Ch. 10** |
| 8 | they work on startups, things they want to build | 0.219 | — |
| 9 | having started it, they must finish it | 0.328 | — |
| 10 | feeling stuck | 0.221 | — |
| 11 | what they would do instead | 0.223 | — |
| 12 | two weeks at most | 0.183 | — |
| 13 | agreeing to keep at it | 0.216 | — |

---

## What this says about the gate

**The headline number is misleading, and in the flattering direction is not the one you
would guess.** Three grounded out of thirteen sounds like the gate is far too strict.
Read the turns and it is close to right.

A real conversation is not thirteen questions. It is two or three questions with ten
short replies hanging off them — *"feeling stuck"*, *"two weeks at most"*, *"yes, I'll
keep at it"*. Those replies have no philosophical content of their own to retrieve
against; they are answers to something **he** just asked. Grounding them would be wrong.
The eval sets never contained a single turn of this shape, because a written question set
cannot have follow-ups.

**The turns that carried the weight are the ones that cleared it.** Turn 2 is the caller
correcting themselves — *clarity* was not it, they are chasing *certainty* — and that is
precisely Book 2 Chapter 1, on why the thing feared is not the thing that harms. Turn 7
reframes a stalled project as the cost of the time it is eating, and pulls Book 4 on
freedom. Both are the moment a conversation turns into a question, and both cleared 0.36
without help.

**Two near-misses, and they are honest ones.** Turn 6 (0.310) and turn 9 (0.328) are the
sunk-cost turns — *it is not going as hoped* and *having started it, I must finish*. The
Discourses has real things to say about both, and at 0.30 the gate would have caught
them. It would also have caught turn 1 (0.318), which is vaguer, and it sits only 0.02
above *"what's on my calendar tomorrow?"* at 0.354 — which is the turn the gate exists to
refuse. **There is no threshold that takes turn 9 and refuses the calendar question.**
That is not a tuning failure; the two turns genuinely look alike to an embedding.

So 0.36 stays. The cost is visible and small: he answers those turns from his own
knowledge of himself, which is not nothing, and the source panel honestly shows blank.

---

## What it does *not* tell us

1. **Thirteen turns, one call, one caller.** Everything above is a reading of a single
   conversation. It is enough to say the design works and the gate is not obviously
   wrong; it is not enough to move a number on.
2. **No tool fired.** `look_up_modern_thing`, `search_my_notion` and `write_to_journal`
   were all available and none came up naturally. They are verified separately, in text.
   *(Later the same day, this finding is what turned `write_to_journal` into
   `write_to_session_log` — a tool that only fires on an explicit resolution is a tool
   that never fires. See `what-makes-each-tool-fire.md`. The other two are unchanged, and
   the retrieval numbers in this file are unaffected.)*
3. **Nothing here measures whether the answers were any good** — only which passages went
   into the prompt. Quality of the reply is a human judgement and was not scored.

---

## How to reproduce

Start the worker, open the deployed link, and talk. The gate logs one privacy-safe
decision line per searchable turn: input character count, selected citations, cosine
score, and which side of the gate it fell on:

```bash
grep "retrieval.search\]" worker.log | grep -v "ready:"
```

That decision line is enough to verify the gate without retaining the caller's words in
hosted logs. The paraphrased turns earlier in this document are the human-readable record
used for this write-up.
