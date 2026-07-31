# What to say to make each tool fire

**Date:** 2026-07-31
**What this is for:** the first live call ran thirteen turns and fired **no tools**.
Nothing was broken — it was a conversation about the caller's research, and none of the
three tools was relevant to any of it. But the brief grades tool calls and the video has
to show one, so this records the sentences that reliably trigger each, verified against
the real APIs. It also records the redesign that came out of that finding: the write tool
was rebuilt as a session log so that it fires on its own, several times a call.
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
| `write_to_session_log` | nothing — it fires on its own (see below) | writes a line and carries on talking |

**The pattern that fires the two read tools.** Both need the caller to reach for something
*outside the conversation*: a thing from the modern world he could not know, or something
they wrote down earlier. Philosophy alone never triggers either, which is why thirteen
turns of it triggered none.

**The write tool is the exception, and that is the change made on 2026-07-31.** It used
to be `write_to_journal` and it only fired on an explicit resolution — *"I resolve to
finish the draft by Friday, write that down"*. That is a rare sentence, so the tool was
effectively invisible: the first live call ran thirteen turns and never used it. It is
now a running log of the conversation, and the persona instruction makes keeping it
non-optional, with an explicit test — *if they have just said something they would not
have said to a stranger an hour ago, that line goes in*.

Measured over a five-turn conversation in which nobody asks him to write anything
(`eval/tools/session_log_check.py`):

| turn | said | wrote |
|---|---|---|
| 1 | "hi. someone told me to talk to you" | — |
| 2 | putting off sending a piece of writing for three weeks | — |
| 3 | "I'd rather it stay unfinished than have someone decide it is not good enough" | ✓ |
| 4 | "I am afraid she will think I am slower than she hired me to be" | ✓ |
| 5 | "I will send it tomorrow morning before I open anything else" | ✓ |

Three entries, all in the caller's own words, none asked for. The greeting and the vague
opener were passed over, which is the half of this that is easy to break: an instruction
strong enough to fire unprompted is also strong enough to fire on *"can you hear me"*.
`tool_check.py` carries that negative case as a fourth prompt for exactly that reason.

**The log starts empty on every call.** Unlike the demo notes, nothing is seeded. So a
non-empty log is proof the write ran — there is no other way for a line to get into it.
Each write also comes back numbered, which is what lets him say "that is the third thing
I have written down" out loud.

---

## Which backend answers

Both personal tools go through `LifeSource`, which picks a backend per call:

- **No passphrase → demo.** `search_my_notion` reads a seeded week,
  `write_to_session_log` appends to an in-memory list that lives for the length of the
  call. He can read entries back in the same conversation; nothing reaches Notion.
  **This is what a normal call gets, and what the video will show.**
- **Passphrase → live Notion**, if the credentials work. Right now they do not: the token
  authenticates, but the integration has no access to any page (search returns zero
  pages, the log page id returns 404). That is a sharing setting in Notion's UI, not
  a code problem, and `LifeSource` falls back to demo either way — which is why calls
  work regardless.

`look_up_modern_thing` has no backends. It is Tavily on every call.

---

## Reproduce

```bash
python eval/tools/tool_check.py           # one prompt per tool, plus the negative case
python eval/tools/session_log_check.py    # the five-turn conversation above
```

`tool_check.py` takes an optional filter — `python eval/tools/tool_check.py log` runs only
the session-log prompts, which is one model call instead of four when iterating on wording.

Text mode is used deliberately in both: `AgentSession.run()` does not invoke
`on_user_turn_completed`, so retrieval is out of the picture and the only thing being
measured is tool dispatch.

One caveat worth stating: this proves the model *chooses* the tool and the tool *returns*.
It does not prove the browser's activity panel renders it — that needs a real call, and is
the thing the video is for.
