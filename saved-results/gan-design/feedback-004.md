# GAN Design Evaluation — Cycle 004

**Date:** 2026-07-31
**Mode:** local-only final evaluation
**Previous strict score:** 7.58 / 10
**Current strict score:** 7.67 / 10
**Change:** +0.09

## Final verdicts

| Question | Verdict | Score |
|---|---|---:|
| **A. Was the app's design objective achieved?** | **PASS** | **8.34 / 10 visual-only** |
| **B. Does the deployed full system pass the strict GAN contract?** | **FAIL** | **7.67 / 10 weighted** |

The visual-only score normalizes Design, Originality, and Craft:

```text
(8.3*.30 + 8.6*.20 + 8.2*.30) / .80 = 8.34
```

The strict score includes Functionality:

```text
8.3*.30 + 8.6*.20 + 8.2*.30 + 5.0*.20 = 7.67
```

The design objective passes because the remaining confirmed desktop layout
defect is fixed and the full Start -> Live -> Review visual system exceeds the
design bar. The strict deployed system still fails because the worker reached by
the retained connected test sends the legacy commitment message and loses the
caller's Next step. That external runtime was not changed in iteration 003.

## Rubric score

| Criterion | Weight | Score | Weighted contribution |
|---|---:|---:|---:|
| Design Quality | 0.30 | 8.3 | 2.49 |
| Originality | 0.20 | 8.6 | 1.72 |
| Craft | 0.30 | 8.2 | 2.46 |
| Functionality | 0.20 | 5.0 | 1.00 |
| **Strict total** | **1.00** |  | **7.67** |

Functionality remains capped at 5 under the binding rubric because the deployed
commitment handoff is a broken core path. The current design score is not reduced
for an external worker version that this design-only iteration did not change.

## Fresh cycle-004 evidence

The live browser fixture uses the current production classes with 12 long
transcript turns, four long source passages, one activity, and the live footer.
It changes only a disposable local browser tab.

### Desktop 1280x720

Fresh settled measurement:

```json
{
  "viewport": { "width": 1280, "height": 720 },
  "documentHeight": 720,
  "shellHeight": 720,
  "footerTop": 620.609375,
  "footerBottom": 681.609375,
  "footerInViewport": true,
  "transcriptScrollable": true,
  "evidenceScrollable": true,
  "horizontalOverflow": false
}
```

Screenshots:

- `saved-results/gan-design/cycle-004/live-long-desktop-1280x720.png`
- `saved-results/gan-design/cycle-004/live-long-desktop-annotated.png`

This fixes the cycle-003 desktop failure. The masthead, independently scrolling
transcript, independently scrolling evidence, activity, status, Mute, and End
Call are simultaneously reachable inside one 720px viewport.

### Mobile 320x568

Fresh measurement:

```json
{
  "viewport": { "width": 320, "height": 568 },
  "documentHeight": 2094,
  "documentWidth": 320,
  "footerTop": 499,
  "footerBottom": 568,
  "footerInViewport": true,
  "endCallHeight": 44,
  "endCallWhiteSpace": "nowrap",
  "horizontalOverflow": false
}
```

Screenshots:

- `saved-results/gan-design/cycle-004/live-long-mobile-320x568.png`
- `saved-results/gan-design/cycle-004/live-long-mobile-annotated.png`

The mobile path intentionally remains a long reading page. Its sticky controls
stay in the viewport, End Call remains one line and 44px high, and neither the
page nor the control bar forces horizontal scrolling.

## Preservation check

The exact starting comment is restored at `web/app/globals.css:131`:

```css
/* A simple white-line portrait on transparency, kept legible at logo size. */
```

The dedicated connected-call class is present only on the live frame, and the
height/overflow rules remain inside the desktop media query. Start, Review, and
the below-900px mobile path are not confined by the desktop rule.

## Retained connected evidence

Cycle 003 remains the live integration source because cycle 004 was explicitly
forbidden from making external or paid calls. That retained evidence verifies:

- admission and microphone-fed conversation;
- 12 two-speaker transcript turns;
- Speaking and Thinking state changes;
- four source passages with citation, title, text, and three-decimal score;
- two tool activities;
- Mute -> Unmute -> Mute;
- End Call into an editable review with 1,091 transcript characters.

The current local viewport fix changes only layout and does not invalidate those
behavioral observations.

## Strict full-system blocker

The retained raw live message from the deployed worker contains only legacy
`action` and `detail` fields. The current repository worker publishes typed
`kind: "commitment"` and `commitment` fields, and the current frontend correctly
requires that typed shape before setting Review Next step. Iteration 003 changed
only the connected shell class, desktop layout CSS, browser regression fixture,
design test, and restored comment. It did not change worker or review behavior.

Therefore:

- **repository design status:** fixed and passing;
- **repository typed commitment contract:** present according to the independent
  final judge's code/deployment comparison;
- **deployed runtime status:** still stale and failing until the current worker
  is redeployed and re-tested;
- **safe response:** redeploy the worker, not add a frontend fallback that might
  turn ordinary reflections into commitments.

## Remaining evidence limits

1. Authenticated Notion database selection, save failure, save success, visible
   disabled `Saved`, and duplicate-save prevention remain unverified because no
   OAuth or authenticated save was allowed.
2. The final 200% browser-zoom check remains unverified because the available
   browser did not support changing page zoom through its automation shortcut.
3. Two zero-similarity passages in cycle 003 remain a retrieval-quality concern,
   not a regression introduced by the redesign or viewport repair.

These limits prevent an unqualified production-readiness claim. The first two
are unverified paths, not proven design defects.

## Regressions

None found. The desktop correction preserves the 320px sticky-footer behavior,
44px controls, one-line End Call, no horizontal overflow, editorial hierarchy,
focus treatment, recovery placement, and review editability established in prior
cycles.

## Plateau and stop rule

Cycle 003 changed by -0.33 and cycle 004 improved by only +0.09. These are two
consecutive cycles with improvement below 0.2, so the GAN plateau stop rule is
now reached. This report ends the loop as required.

## Final handoff

The design request is complete and passes its visual objective at 8.34. Do not
claim a strict full-system GAN pass. The smallest remaining action is external to
this worktree: redeploy the current worker, then run one short call proving that
the raw typed commitment exactly reaches Review Next step. Authenticated Notion
and 200% zoom proof remain separate evidence gates.
