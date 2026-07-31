# What to say to make each tool fire

**Date:** 2026-07-31
**What this is for:** the first live call ran thirteen turns and fired **no tools**.
Nothing was broken — it was a conversation about the caller's research, and none of the
three tools was relevant to any of it. But the brief grades tool calls and the video has
to show one, so this records the sentences that reliably trigger each, verified against
the real APIs.
**Who should read it:** whoever records the video, and anyone who thinks the tools are
broken because a call went by without one.

---

## The three tools, and what fires them

Verified 2026-07-31 in text mode against the live model and live APIs. All three fired on
the first attempt, with no coaxing.

| tool | say something like | what came back |
|---|---|---|
| `look_up_modern_thing` | *"my therapist keeps telling me to try something called cold plunging — what even is that"* | a real Tavily search, then him explaining it in his own words |
| `search_my_notion` | *"what did I write in my notes about work? can you look?"* | reads the notes back, then presses on what they say |
| `write_to_journal` | *"I resolve to finish the draft by Friday and stop rewriting the intro — write that down"* | writes it, then asks what they will actually do first |

**The pattern that fires them.** Each tool needs the caller to reach for something
*outside the conversation*: a thing from the modern world he could not know, something
they wrote down earlier, or a resolution they want kept. Philosophy alone never triggers
one, which is why thirteen turns of it triggered none.

**`write_to_journal` also wants a resolution, not a wish.** Its description tells him to
use it once they have said what they will actually do. *"I should probably work harder"*
does not fire it; *"I will finish the draft by Friday"* does.

---

## Which backend answers

Both personal tools go through `LifeSource`, which picks a backend per call:

- **No passphrase → demo.** `search_my_notion` reads a seeded week, `write_to_journal`
  appends to an in-memory list that lives for the length of the call. He can read the
  entry back in the same conversation; nothing reaches Notion. **This is what a normal
  call gets, and what the video will show.**
- **Passphrase → live Notion**, if the credentials work. Right now they do not: the token
  authenticates, but the integration has no access to any page (search returns zero
  pages, the journal page id returns 404). That is a sharing setting in Notion's UI, not
  a code problem, and `LifeSource` falls back to demo either way — which is why calls
  work regardless.

`look_up_modern_thing` has no backends. It is Tavily on every call.

---

## Reproduce

`scratchpad/tool_check.py` runs the three prompts through the real agent in text mode and
prints which tool fired for each. Text mode is used deliberately: `AgentSession.run()`
does not invoke `on_user_turn_completed`, so retrieval is out of the picture and the only
thing being measured is tool dispatch.

One caveat worth stating: this proves the model *chooses* the tool and the tool *returns*.
It does not prove the browser's activity panel renders it — that needs a real call, and is
the thing the video is for.
