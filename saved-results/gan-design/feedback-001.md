# GAN Design Evaluation — Cycle 001

**Date:** 2026-07-31
**App:** `http://127.0.0.1:3000`
**Result:** FAIL
**Weighted score:** 7.26 / 10

## First-principles standard

A strong Epictetus voice app must make three things immediately clear: the start
screen is an invitation to speak, the live screen is a conversation whose claims
are visibly grounded, and the review screen is the caller's editable record. The
portrait, reading type, warm rule, evidence rail, and next-step emphasis must make
this product recognizable even without its name. The primary action must be
obvious in every state, while proof and optional Notion saving remain secondary.

High visual quality is not enough by itself. At 1280x720 and 320x568, the app must
avoid overflow and covered content; keyboard order and focus must follow the
visible reading order; loading and errors must remain beside the action that can
recover; and the real call, transcript, sources, activity, mute, review, and save
paths need live evidence.

## Scores

| Criterion | Weight | Score | Weighted contribution |
|---|---:|---:|---:|
| Design Quality | 0.30 | 7.8 | 2.34 |
| Originality | 0.20 | 8.4 | 1.68 |
| Craft | 0.30 | 6.8 | 2.04 |
| Functionality | 0.20 | 6.0 | 1.20 |
| **Total** | **1.00** |  | **7.26** |

The cycle fails because the weighted score is below 8.0, Craft and Functionality
are below 7, and the required connected-call evidence is incomplete. No core path
is proven broken: the real call stopped because this headless Chromium reports
`NotSupportedError` for microphone capture. That environment limit is separate
from the app defects below.

## Evidence

All screenshots were captured from the live app and opened for visual inspection.
The fake admission and injected review data mentioned below changed browser runtime
state only; no app code was changed.

### Start

- `saved-results/gan-design/cycle-001/start-desktop.png` — 1280x720 desktop, full page.
- `saved-results/gan-design/cycle-001/start-desktop-focus-start.png` — 1280x720, Start focus ring.
- `saved-results/gan-design/cycle-001/start-mobile-320x568.png` — 320x568 mobile.
- `saved-results/gan-design/cycle-001/start-loading-mobile.png` — runtime loading state, disabled `Waking him…` button.
- `saved-results/gan-design/cycle-001/notion-error-placement-mobile.png` — Notion callback error placed below Start instead of inside the Notion section.
- `saved-results/gan-design/cycle-001/notion-connected-long-mobile.png` — runtime-only connected Notion layout with long workspace and database names.

### Live

- `saved-results/gan-design/cycle-001/live-desktop-settled.png` — 1280x720 connecting shell rendered with a fake, non-billable admission.
- `saved-results/gan-design/cycle-001/live-mobile-320x568.png` — 320x568 connecting shell and sticky controls.
- `saved-results/gan-design/cycle-001/live-mobile-320x568-bottom.png` — bottom-of-page mobile check.

The fake admission was used only because the single real attempt could not obtain
a microphone in this headless browser. It verifies layout and the End Call state
transition, not audio, transcript delivery, source messages, or tool activity.

### Review

- `saved-results/gan-design/cycle-001/review-desktop.png` — 1280px full review with injected sample content.
- `saved-results/gan-design/cycle-001/review-desktop-viewport.png` — 1280x720 edited-field viewport.
- `saved-results/gan-design/cycle-001/review-mobile-320x568.png` — 320x568 review, including inline draft failure and no-database state.
- `saved-results/gan-design/cycle-001/end-call-review-mobile.png` — fake live admission ended into an editable empty review.
- `saved-results/gan-design/cycle-001/new-call-mobile.png` — New call returned to setup.

## Ranked issues

### 1. Notion errors appear under the call action

**Severity:** high craft and recovery issue
**Screen / viewport:** start, 320x568
**Selectors:** `.failure`, `.notion-connect`

Opening a Notion callback error rendered the `role="alert"` paragraph directly
below `Start Call`. Browser inspection confirmed `failure.closest('.notion-connect')`
is false. The message is readable, but its location says the call failed and puts
it away from the `Connect Notion` control that can recover.

**Required outcome:** token/room failures stay below Start; Notion load, callback,
selection, and disconnect failures render inside `.notion-connect` below the
relevant Notion control. Keep `role="alert"` and plain language.

### 2. Room failures expose transport wording

**Severity:** high recovery issue
**Screen / viewport:** start after the real call attempt, 1280x720 and 320x568
**Selector:** `.failure`

The app correctly returned to setup and left Start usable, but showed messages
such as `Client initiated disconnect` and `could not establish signal connection:
Abort handler called`. These describe LiveKit internals, not what the caller can
do next.

**Required outcome:** translate expected connection and microphone failures into
a short recovery message, for example that the call could not connect and the
caller should check microphone access and try again. Keep the detailed error in
diagnostic logging, not in the visible copy.

### 3. The review destination breaks into three narrow lines

**Severity:** medium visual craft issue
**Screen / viewport:** review, 320x568
**Selector:** `.review-masthead .destination`

`CALL COMPLETE` stacks as `CALL` / `COMPLET` / `E`. It looks accidental and
competes with the two-line `Evening Review` title.

**Required outcome:** give the destination a deliberate compact mobile position
that keeps the two words intact without horizontal overflow. Verify at 320px.

### 4. End Call wraps on the narrow live control bar

**Severity:** medium control craft issue
**Screen / viewport:** live, 320x568
**Selector:** `.live-controls .danger`

`End Call` wraps onto two lines while `Unmute` remains on one. The action still
works and remains at least 44px high, but the unequal labels make the fixed bar
look squeezed at the narrowest required width.

**Required outcome:** keep `End Call` on one line at 320px while retaining the
status, 44px targets, safe-area padding, and no horizontal overflow.

### 5. Connected-call proof is missing for this cycle

**Severity:** pass blocker, environment limit rather than a confirmed app bug

The real Start click reached admission, but microphone capture returned
`NotSupportedError: Not supported` in the headless browser. The app returned to
setup with an inline alert. Because no connected room was available, this cycle
could not verify audible agent audio, real speaker attribution, transcript
autoscroll, source replacement/clearing, source scores, tool activity, commitment
capture, or a real mute/unmute transition.

**Required outcome for the next evaluation:** run one short call in a browser with
fake audio capture or real microphone permission and capture desktop plus 320px
evidence for transcript, sources, activity, Mute/Unmute, and End Call into review.
This does not require a product-code workaround for the evaluator environment.

## Verified wins

- The start composition is specific to this product: the large line portrait is
  structural, the quote is the first reading target, and the warm rule connects
  explanation and action. It does not read as a renamed chatbot dashboard.
- Start, empty live, and review share one restrained stone, ink, lamp, rule, and
  serif/sans system without glass, shadows, chat bubbles, or floating cards.
- No horizontal overflow was found at 1280x720 or 320x568 in start, empty live,
  review, or the long connected-Notion runtime state.
- On setup, keyboard order was Start then Connect Notion. Both showed the required
  2px gold outline with a 3px offset. Review fields exposed Title, Summary, Next
  step, Transcript, then New call in DOM order; inspected app fields showed the
  same focus treatment. Extra initial stops in the development build came from
  the Next.js developer portal and are not counted as app controls.
- `Waking him…` remained visible while Start was disabled. Long workspace and
  database names wrapped or truncated without forcing overflow.
- The fake live state kept the 320px control bar pinned to the viewport bottom,
  and the empty content remained scrollable. End Call created the review before
  the fake room disconnected.
- Title, Summary, Next step, and Transcript were all editable. An automatic-draft
  failure stayed inline and left all fields usable. With no selected database,
  no Save button appeared. New call returned to setup.

## Functionality coverage and limits

| Path | Result |
|---|---|
| Random attributed quote | Verified across reloads; text and Discourses citation changed together. |
| Start loading | Verified with runtime state: only Start disabled and label became `Waking him…`. |
| Token/call error recovery | Real click returned to usable setup with inline `role="alert"`; visible copy is too technical. |
| Optional Notion disconnected state | Verified visually and by keyboard. OAuth was not opened. |
| Connected Notion, long database, disconnect control | Runtime-only layout verification; no overflow. Backend selection/disconnect not exercised. |
| Connected room and microphone publication | Not verified; headless microphone capture is unsupported. |
| Audible agent, transcript, source replacement/clear, activity | Not verified; requires a connected room. |
| Mute/unmute | Pressed state and label were visible in the fake live shell; actual microphone transition not verified. |
| End Call to review | Verified with fake admission; empty editable review appeared. |
| Draft success | Not verified. Draft failure recovery was verified and remained editable. |
| Save failure/success/idempotence | Not tested because no authenticated Notion database was available, as required by the evaluation brief. |
| New call | Verified from injected review; setup returned and the quote refreshed. |

## Generator iteration 002 contract

1. Split call and Notion failure presentation so each alert sits under the action
   that can recover it. Add or update tests that fail before this change.
2. Map expected room and microphone failures to plain recovery copy while keeping
   detailed context in existing diagnostic logs.
3. Repair `.review-masthead .destination` at 320px so `CALL COMPLETE` never breaks
   inside a word and does not cause horizontal overflow.
4. Repair `.live-controls .danger` at 320px so `End Call` remains one line without
   shrinking any target below 44px or covering content.
5. Preserve the distinctive start portrait, editorial quote hierarchy, evidence
   rail, next-step rule, focus ring, long-name handling, and no-card visual system.
6. Re-run the focused design tests, full tests, type check, build, and browser
   screenshots at 1280x720 and 320x568. The next evaluator must separately obtain
   connected-call evidence; do not add a production-only bypass for that purpose.

## Plateau

Not applicable. This is the first scored cycle.
