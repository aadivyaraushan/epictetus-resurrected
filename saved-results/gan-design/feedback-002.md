# GAN Design Evaluation — Cycle 002

**Date:** 2026-07-31
**App:** `http://127.0.0.1:3000`
**Cycle 1 score:** 7.26 / 10
**Cycle 2 score:** 7.91 / 10
**Change:** +0.65
**Result:** FAIL

## Standard

The app must read as one specific Epictetus product across invitation, grounded
conversation, and editable record. The portrait, warm rule, reading type,
evidence rail, and next-step emphasis must create that identity without hiding
the primary action. At 1280x720 and 320x568, controls must stay reachable,
44px or taller, keyboard-visible, free of overflow, and paired with recovery
messages in the section that can fix the failure. A pass also requires live
evidence for the real call, transcript, grounding, activity, microphone, review,
and optional save rules.

## Scores

| Criterion | Weight | Score | Weighted contribution |
|---|---:|---:|---:|
| Design Quality | 0.30 | 8.3 | 2.49 |
| Originality | 0.20 | 8.6 | 1.72 |
| Craft | 0.30 | 8.0 | 2.40 |
| Functionality | 0.20 | 6.5 | 1.30 |
| **Total** | **1.00** |  | **7.91** |

This cycle fails because the weighted score is below 8.0, Functionality is below
7, and connected-call evidence remains incomplete. The same headless microphone
limit from cycle 1 is not counted against Design, Originality, or Craft. No core
path is proven broken by this result.

## Cycle-1 contract verification

| Requirement | Live result | Evidence |
|---|---|---|
| Notion alerts stay in the Notion section | Fixed. The alert text was `Could not connect Notion. Try connecting again.` and `closest('.notion-connect')` was true; `closest('.warm-spine')` was false. | `cycle-002/notion-error-mobile-320x568.png` |
| Call failures stay with Start and use plain copy | Fixed. The one real admission attempt returned `The call could not connect. Check microphone access, then try again.` Start was enabled again, and the alert was inside `.warm-spine`, not `.notion-connect`. | `cycle-002/real-call-recovery-desktop.png` |
| `CALL COMPLETE` stays intact at 320px | Fixed. Computed `white-space` was `nowrap`; the 288px destination rendered as one line with no horizontal overflow. | `cycle-002/review-mobile-top-320x568.png` |
| `End Call` stays intact and at least 44px | Fixed. At 320px it measured 78.67 x 44px, used `white-space: nowrap`, stayed on one line, and caused no overflow. | `cycle-002/live-mobile-320x568.png` |

## Fresh evidence

All screenshots were captured from the live app and opened for inspection. Fake
admission and review data altered browser runtime state only; app code was not
changed.

### Start

- `saved-results/gan-design/cycle-002/start-desktop-1280x720.png`
- `saved-results/gan-design/cycle-002/start-desktop-annotated.png`
- `saved-results/gan-design/cycle-002/start-mobile-320x568.png`
- `saved-results/gan-design/cycle-002/notion-error-mobile-320x568.png`
- `saved-results/gan-design/cycle-002/real-call-recovery-desktop.png`

### Live

- `saved-results/gan-design/cycle-002/live-desktop-1280x720.png`
- `saved-results/gan-design/cycle-002/live-desktop-annotated.png`
- `saved-results/gan-design/cycle-002/live-mobile-320x568.png`
- `saved-results/gan-design/cycle-002/live-mobile-annotated.png`
- `saved-results/gan-design/cycle-002/live-mobile-bottom-320x568.png`
- `saved-results/gan-design/cycle-002/live-mobile-focus-end.png`

At the 320px bottom position, the evidence rail ended 24px above the sticky
control bar. The document width remained 320px. The live controls measured 69px
high; both buttons measured 44px high.

### Review

- `saved-results/gan-design/cycle-002/end-call-review-mobile.png`
- `saved-results/gan-design/cycle-002/review-mobile-top-320x568.png`
- `saved-results/gan-design/cycle-002/review-mobile-320x568.png`
- `saved-results/gan-design/cycle-002/review-desktop-top-1280x720.png`
- `saved-results/gan-design/cycle-002/review-desktop-1280x720.png`
- `saved-results/gan-design/cycle-002/review-desktop-annotated.png`

## Verified product quality

- The start portrait remains a major structural element; the quote, citation,
  explanation, Start action, and optional Notion section have a clear reading
  order at desktop and mobile sizes.
- Start, empty live, and review retain one coherent stone, ink, lamp, rule, and
  serif/sans system without generic cards, glass, shadows, chat bubbles, or
  oversized pills.
- No horizontal overflow was found on start, live, or review at 1280x720 or
  320x568.
- Setup keyboard order was Start then Connect Notion. Both showed the required
  2px gold outline with a 3px offset.
- Live keyboard order was Unmute then End Call; Tab gave End Call the required
  2px gold outline with a 3px offset. `aria-pressed` remained present on Unmute.
- Review keyboard order was Title, Summary, Next step, Transcript, New call.
  Title and New call showed the same required focus treatment.
- End Call produced an editable review before the fake room disconnected. Title,
  Summary, Next step, and Transcript all accepted edits. With no selected Notion
  database, no Save button appeared.
- New call returned to setup, refreshed the quote, and retained the optional
  Notion section.
- The mobile evidence rail cleared the sticky controls at the page bottom; no
  last item was covered.

## Remaining pass blocker

The single real admission attempt again reached the room path, but this headless
Chromium cannot provide a microphone (`getUserMedia` reports `NotSupportedError`).
The app handled that failure correctly and returned to setup with plain recovery
copy. Because the room never connected, this cycle still cannot verify:

- microphone publication and a real Mute/Unmute transition;
- audible agent output and listening/thinking/speaking changes;
- two-speaker transcript delivery and near-bottom autoscroll;
- grounding source replacement and clearing, including visible scores;
- tool activity and commitment capture into review;
- a successful automatic review draft from a real transcript.

This is an evaluator-environment limit, not a confirmed app defect. The exact
200% browser-zoom check was also unavailable: five `Meta++` shortcuts left
`innerWidth`, `devicePixelRatio`, and `visualViewport.scale` unchanged. Required
320px evidence passed, but the unsupported shortcut is not claimed as 200% proof.

Notion OAuth and authenticated save were intentionally not attempted. Therefore
database selection, save failure, save success, and duplicate-save prevention
remain unverified beyond their visible conditional states.

## Regressions

None found. The cycle-1 visual identity, responsive layout, focus treatment,
long-name safety, review editability, and no-card system remain intact.

## Iteration-3 contract

No further product-code change is justified by cycle-2 evidence. The four known
app defects are fixed, and adding a production bypass solely for evaluation would
weaken the product contract.

Iteration 3 should be evaluator-only unless new live evidence reveals a defect:

1. Use a browser with fake audio capture or real microphone permission.
2. Run one short connected call and capture desktop plus 320px evidence showing
   microphone publication, agent audio/state, both transcript speakers, at least
   one grounding passage with citation/title/text/three-decimal score, tool
   activity, commitment capture, Mute then Unmute, and End Call into review.
3. Confirm the transcript and commitment arrive in review and the draft success
   or inline failure state remains editable.
4. If an authenticated test Notion workspace is supplied, verify database choice,
   Save failure recovery, Save success, disabled `Saved`, and no second page from
   another click. Otherwise keep this explicitly unverified.
5. Run the required 200% zoom check in a browser that supports page zoom.
6. Preserve all cycle-2 visuals and recovery behavior unless connected evidence
   exposes a specific defect.

## Plateau

Not reached. Cycle 2 improved by 0.65 points over 7.26, above the 0.2 threshold.
