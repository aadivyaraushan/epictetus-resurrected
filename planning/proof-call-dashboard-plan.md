# Proof Call Dashboard Plan

**Date:** 2026-07-31
**Purpose:** record one live call that visibly proves room admission, RAG decisions,
tool use, and the normal conversation without changing the public home page.

```text
/proof -> POST /api/token -> safe admission facts -------------------+
                                                                    |
microphone -> transcript turn --------------------------------------+--> one ordered proof timeline
                                                                    |
worker -> epictetus.sources -> RAG decision + selected passages ----+
       -> epictetus.activity -> tool call --------------------------+

/ -> existing start, call, evidence rail, and review (unchanged)
```

## Done

- Anyone with the exact `/proof` URL can open it; the normal page does not link to it.
- One call shows the ordinary transcript with room, RAG, and tool events inserted
  between the turns where they happened.
- The room event shows only safe facts: room name, 30-minute lifetime, allowed
  actions, and `epictetus` dispatch. It never renders the signed token or secrets.
- Every searchable turn records its score, the `0.2315` minimum, the `0.36`
  automatic-accept boundary, any Luna decision, and the selected passages. Short
  turns and retrieval errors are also visible instead of looking like missing
  instrumentation.
- Ending the proof call reaches the same review flow as the normal call.
- Desktop and mobile layouts remain readable and match the existing visual system.

## Build and verification

1. Add failing Python tests for the RAG event payload and failing web tests for
   safe admission facts, event ordering, `/proof`, and unchanged `/` behavior.
2. Run the focused tests and retain the expected failures.
3. Add the minimum safe event data to the existing token and source messages.
4. Extract the shared call experience, add `/proof`, and render the chronological
   proof timeline without changing the normal live-call components.
5. Run focused tests, the full Python and web suites, type checking, and production
   build.
6. Run the app and inspect `/` and `/proof` at desktop and mobile sizes. If browser
   control is unavailable, use screenshots and record that limit.
7. Have a fresh judge compare the finished result with this plan and the take-home
   requirements, then fix any concrete gap before handoff.

## Boundaries

- No authentication: obscurity of the unlinked URL is the chosen access model.
- No raw server logs, credentials, signed tokens, or unrelated caller data.
- No change to retrieval behavior, prompts, thresholds, model choices, or tool
  selection. This work exposes existing decisions; it does not tune them.
- Do not touch the untracked RAG diagnosis files in the main worktree.

## Verification record

- Focused red run: four backend failures because RAG metadata did not exist;
  web failures because the proof route, admission facts, and event module did not exist.
- Green: 46 Python tests, 62 web tests, TypeScript check, and Next.js production build.
- Production build lists `/proof` as a statically generated route.
- Computer Use opened `http://localhost:3000/proof` and confirmed the approved start
  screen renders cleanly. A real proof call was not started because that would use
  paid voice services and the isolated worktree intentionally has no copied secrets.
- Independent review passed. Its concrete presentation finding was fixed: RAG
  annotations now include the worker's detailed grounded/rejected/skipped/error reason.
