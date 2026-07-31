# GAN Design Generator — Iteration 003

**Date:** 2026-07-31
**Worktree:** `/Users/aadivyar/Documents/Internships/Bluejay Take Home-gan-design`
**Input:** `saved-results/gan-design/final-judge.md`
**Purpose:** Fix only the confirmed desktop live viewport defect and restore the missed starting comment.

## Observable done conditions

1. The connected desktop call is exactly one viewport tall at `1280x720`.
2. Mute and End Call stay inside that viewport with dense transcript and source content.
3. Transcript and evidence scroll independently on desktop.
4. Below 900px, the existing long page and sticky control behavior remains unchanged.
5. The exact original portrait comment is present again.

## Source-contract red

Command, run before implementation from `web/`:

```text
npm test -- call/design-contract/ui-structure.test.ts
```

Exact result:

```text
Test Files  1 failed (1)
Tests       1 failed | 6 passed (7)
Duration    1.25s
```

The new test failed because the connected room still used only `className="shell"`; no dedicated live-shell hook, desktop viewport confinement, independent-scroller rules, or restored portrait comment existed.

## Browser regression red

The reusable fixture `web/call/design-contract/live-viewport.browser.js` replaced one local test tab's body with the real live layout classes, 12 transcript turns, four long source passages, one activity, and the footer. The tab was `1280x720`; no production file or backend state was changed.

Exact pre-fix measurement:

```json
{
  "viewport": { "width": 1280, "height": 720 },
  "documentHeight": 1676,
  "shellHeight": 1669.8046875,
  "footerTop": 1576.40625,
  "footerBottom": 1637.40625,
  "footerInViewport": false,
  "transcriptScrollable": false,
  "evidenceScrollable": false,
  "horizontalOverflow": false
}
```

## Implementation

- Added `live-shell` only to the connected `LiveKitRoom` frame.
- Above 900px, fixed that shell to `100dvh`, hid page-level overflow, preserved `min-height: 0` through the grid and evidence flex chain, and retained `overflow-y: auto` on both scrollers.
- Kept every new height rule inside `@media (min-width: 900px)`, so the existing mobile long-page and sticky footer path remains the active behavior below 900px.
- Restored the exact comment `A simple white-line portrait on transparency, kept legible at logo size.` above `img.mark`.

## Green verification

Focused source contract:

```text
$ npm test -- call/design-contract/ui-structure.test.ts
Test Files  1 passed (1)
Tests       7 passed (7)
Duration    327ms
```

Same `1280x720` browser fixture after the fix:

```json
{
  "viewport": { "width": 1280, "height": 720 },
  "documentHeight": 726,
  "shellHeight": 720,
  "footerTop": 626.6015625,
  "footerBottom": 687.6015625,
  "footerInViewport": true,
  "transcriptScrollable": true,
  "evidenceScrollable": true,
  "horizontalOverflow": false
}
```

The six extra document pixels were measured during the existing 220ms page-entry transform. The layout box itself is exactly 720px and the complete footer remains inside the 720px viewport.

Cycle-2 mobile regression at `320x568`, after the same dense fixture:

```json
{
  "documentHeight": 2094,
  "documentWidth": 320,
  "footerTop": 499,
  "footerBottom": 568,
  "footerInViewport": true,
  "controlsOverflow": false,
  "endCallHeight": 44,
  "endCallWhiteSpace": "nowrap",
  "horizontalOverflow": false
}
```

Full web suite:

```text
$ npm test
Test Files  13 passed (13)
Tests       50 passed (50)
Duration    861ms
```

TypeScript:

```text
$ npx tsc --noEmit
exit 0; no output
```

Production build:

```text
$ npm run build
✓ Compiled successfully in 1368ms
✓ Finished TypeScript in 1437ms
✓ Generating static pages (4/4) in 93ms
exit 0
```

Patch check:

```text
$ git diff --check
exit 0; no output
```

## Files changed in this iteration

- `web/app/page.tsx` — dedicated connected-call shell hook.
- `web/app/globals.css` — desktop-only live confinement and exact restored user comment.
- `web/call/design-contract/ui-structure.test.ts` — source contract for the live hook, desktop confinement, independent scrollers, and comment.
- `web/call/design-contract/live-viewport.browser.js` — reusable dense browser regression fixture and geometry report.
- `saved-results/gan-design/generator-003.md` — this record.

## Sibling search

Searched all `shell`, `live-shell`, `live-layout`, `scroller`, and `live-controls` uses under `web/app` and `web/call`. Only the connected LiveKit frame receives `live-shell`; setup and review keep their existing `shell` variants. The constrained selectors are all scoped to `.live-shell` and the desktop media query, so the review form, start page, and mobile live page are not affected.

Searched for the exact portrait comment and confirmed one restored occurrence in `web/app/globals.css`. No worker, retrieval, review data-flow, or deployment file was edited in this iteration.

## Logging decision

No logging was added because this is presentation-only CSS plus a class hook. Call, error, transcript, source, activity, review, and deployment behavior did not change. The browser check only replaced DOM in a disposable local test tab; the viewport override was reset and the tab was closed afterward.

## Evaluator focus

The evaluator should repeat the dense `1280x720` live call check and confirm the masthead, both independently scrolling reading columns, and complete footer remain simultaneously reachable. It should also retain the `320x568` sticky-footer check. The deployed-worker commitment mismatch and authenticated Notion proof remain outside this narrowly authorized iteration.
