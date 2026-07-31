# Recording-only Proof Call Dashboard

**Date:** 2026-07-31
**Purpose:** give the take-home video one call screen that proves room admission,
RAG decisions, tool use, and the live conversation in chronological order.

## Result

The implementation lives on the unlinked public route `/proof`. The normal `/`
experience keeps its existing transcript and evidence rail. Once a proof call starts,
the route inserts three kinds of annotations directly into the transcript:

1. **Room admitted** — room name, 30-minute lifetime, allowed actions, and named
   worker dispatch. The signed token and server secrets are never rendered.
2. **RAG** — grounded, rejected, skipped, or failed status; hybrid-search method;
   cosine score, the `0.2315` minimum, the `0.36` automatic-accept boundary,
   the Luna decision when needed, and every selected passage.
3. **Tool call** — the action and safe detail already published by the worker.

Streaming transcript segments update in place without moving annotations that were
inserted after them. Ending the call still opens the existing review flow.

## Recording path

1. Open `https://<deployment>/proof`; the public home page does not link to it.
2. Start one call.
3. Ask a reliable RAG question:
   `Why did you compare spending time with certain people to placing quenched charcoal next to burning charcoal?`
4. Trigger the web-search tool:
   `My therapist keeps telling me to try something called cold plunging — what even is that?`
5. Keep the proof timeline visible while explaining the token facts, the hybrid
   vector-plus-BM25 search, and the three score paths: below `0.2315`, Luna from
   `0.2315` to below `0.36`, and automatic acceptance at `0.36` or above.
6. End the call normally.

## Verification

```text
46 Python tests passed
62 web tests passed
TypeScript check passed
Next.js production build passed and emitted /proof
```

Computer Use confirmed the local `/proof` start screen matches the existing visual
system. A real proof call was not run during this verification because it would use
paid voice services and the isolated worktree contains no copied credentials.

## Reuse

After changes to retrieval or tool messages, rerun:

```text
.venv/bin/python -m pytest tests -q
cd web && npm test && npx tsc --noEmit && npm run build
```

The `epictetus.sources` contract is additive: the normal source panel still reads
`sources`, while the proof route also reads the new `rag` object. In the combined
release that object uses `minimumCosine`, `automaticCosine`, and `decision` so a
Luna-approved turn is not mislabelled as having crossed the automatic boundary.
The tool activity contract is unchanged.
