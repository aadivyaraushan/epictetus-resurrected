# GAN Design Generator — Iteration 002

**Date:** 2026-07-31
**Worktree:** `/Users/aadivyar/Documents/Internships/Bluejay Take Home-gan-design`
**Input:** `saved-results/gan-design/feedback-001.md`
**Purpose:** Route recovery messages to the correct start-screen section, replace transport wording with caller-facing copy, and repair two narrow mobile labels.

## Binding outcomes

1. Call failures render below Start; Notion failures render inside the Notion section.
2. Admission and room/microphone failures show short recovery copy while the original error remains in tagged logs.
3. `CALL COMPLETE` and `End Call` remain intact at 320px without reducing 44px targets.
4. The portrait composition, quote hierarchy, evidence rail, next-step rule, focus ring, long-name handling, and open no-card system stay unchanged.

## Red test

Command, run before implementation from `web/`:

```text
npm test -- call/design-contract/ui-structure.test.ts call/start-screen/recovery/call-recovery.test.ts
```

Exact result:

```text
Test Files  2 failed (2)
Tests       2 failed | 4 passed (6)
Duration    780ms
```

The recovery test suite could not load because `call-recovery.ts` did not exist. The design contract also failed because the app still passed one shared failure prop and neither narrow-label CSS rule existed.

## Implementation

- Replaced the single page-level failure state with `callFailure` and `notionFailure`.
- Routed admission and room failures to the Start action, and load/callback/selection/disconnect failures to the Notion section.
- Added one pure recovery-copy mapper. Admission failures show `The call could not start. Please try again.` Room and microphone failures show `The call could not connect. Check microphone access, then try again.`
- Kept original error objects in the existing `[page]` and `[page.notion]` `console.error` calls. Added a tagged callback-error log because the callback message is no longer displayed directly.
- Made the review destination a full-width mobile masthead row and prevented it from wrapping inside either word.
- Prevented the narrow End Call control from shrinking or wrapping.

## Green verification

Focused tests:

```text
$ npm test -- call/design-contract/ui-structure.test.ts call/start-screen/recovery/call-recovery.test.ts
Test Files  2 passed (2)
Tests       8 passed (8)
Duration    590ms
```

Full web suite:

```text
$ npm test
Test Files  13 passed (13)
Tests       49 passed (49)
Duration    1.97s
```

TypeScript:

```text
$ npx tsc --noEmit
exit 0; no output
```

Production build:

```text
$ npm run build
✓ Compiled successfully in 7.4s
✓ Finished TypeScript in 1928ms
✓ Generating static pages (4/4) in 116ms
exit 0
```

Patch check:

```text
$ git diff --check
exit 0; no output
```

## Files changed in this iteration

- `web/app/page.tsx` — separate error state, safe visible recovery copy, and preserved detailed logs.
- `web/call/start-screen/start-screen.tsx` — call and Notion alerts rendered inside their own recovery sections.
- `web/call/start-screen/recovery/call-recovery.ts` — pure caller-facing copy mapper.
- `web/call/start-screen/recovery/call-recovery.test.ts` — admission, room, and microphone recovery-copy tests.
- `web/call/design-contract/ui-structure.test.ts` — alert placement and narrow-label contract tests.
- `web/app/globals.css` — targeted 320px review-destination and End Call rules.
- `saved-results/gan-design/generator-002.md` — this record.

## Sibling search

Searched `web/app`, `web/call`, `web/notion`, and `web/review` for failure setters, `role="alert"`, and `console.error`. The start page was the only shared cross-feature failure state. Review draft/save errors remain in their own review form and source/activity parse errors remain in their own live panels, so those separate contexts were left unchanged.

Searched all `destination`, `live-controls`, `danger`, `End Call`, and `call complete` uses. The targeted selectors cover the single End Call button and the review completion label without changing the live destination's long-name behavior.

Searched for the protected design hooks and confirmed the start portrait, warm spine, evidence rail, next-step field, and gold focus outline remain present.

## Logging decision

Error handling changed, so diagnostic logging was preserved and extended. Admission, room, Notion status, callback, selection, and disconnect failures retain the original technical error in tagged logs. Visible copy is fixed and does not include the transport message. No credentials, token bodies, room tokens, database payloads, or other secrets are logged.

## Evaluator focus

The independent evaluator should verify both alert containers in the live DOM, a real or simulated microphone/room failure's visible copy, and screenshots of review plus live controls at exactly `320x568`. It should also confirm no horizontal overflow, 44px control height, long live destination handling, and the locked iteration-1 design wins. Connected-call evidence still requires the evaluator's fake audio capture or a browser with microphone access; no production bypass was added.
