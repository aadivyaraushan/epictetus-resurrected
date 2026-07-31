# Independent Judge — Original Home Restore

Date: 2026-07-31

## Standard for a strong result

A passing result must:

1. Restore the original home at desktop and mobile sizes: compact portrait masthead, centered quote and explanation, round gold Start Call button, and centered optional Notion section.
2. Preserve working start and Notion behavior, with call errors shown by the call action and Notion errors shown in the Notion section.
3. Leave the improved live-call and review layouts in place.
4. Pass the project tests and production build.

## Verdict: PASS

The saved desktop and mobile screenshots do restore the original home layout. My initial visual reading of those files was wrong: the portrait is present in both new screenshots. Pixel checks prove that the portrait areas are identical to the baseline:

- Desktop crop `(75, 20)` to `(175, 130)`: no differing pixels; mean channel difference `0.0`.
- Mobile crop `(15, 10)` to `(110, 110)`: no differing pixels; mean channel difference `0.0`.
- Each baseline and new crop contains the same 658 bright portrait pixels.

The verified desktop and mobile outputs restore the requested OG composition: compact portrait masthead, centered quote and explanation, round gold Start Call button, divider, and optional Notion action. The quote and citation differ because the page intentionally selects a quote at random; this does not change the layout.

## What is verified as intact

- The original centered structure and styling are restored in `web/call/start-screen/start-screen.tsx` and the scoped `.og-start-shell` rules in `web/app/globals.css`.
- The saved desktop and mobile home screenshots match the OG portrait and composition, apart from the expected random quote change.
- Call and Notion errors remain separate: `web/app/page.tsx` keeps `callFailure` and `notionFailure`, and `web/call/start-screen/start-screen.tsx` renders them in their matching sections.
- The improved live-call and review structures remain present through `live-layout`, `evidence-rail`, `review-layout`, and `review-context`.
- `npm test` passed 50 of 50 tests across 13 files.
- `npm run build` compiled successfully and completed TypeScript and static-page generation.

## Follow-up check

The shared `web/public/epictetus.png` file differs from Git `HEAD`, even though the saved home portrait pixels match the baseline exactly. This does not overturn the verified layout result, but a later browser check should start from a fresh browser context and confirm the expected shared portrait loads with `naturalWidth > 0`; the current structure test only checks that the `mark` class exists.
