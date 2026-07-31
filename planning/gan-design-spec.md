# Epictetus Design Contract

**Date:** 2026-07-31
**Applies to:** start, live call, completed review
**Direction:** dark historical editorial design; quiet, direct, and clearly built for this product
**GAN bounds:** weighted pass score 8.0/10; at most 5 generator-evaluator cycles

```text
ONE VISUAL SYSTEM

  WHITE-LINE PORTRAIT       WARM RULE              EDITORIAL TYPE
  the person is present  +  proof and action   +  conversation, not chat
           |                     |                         |
           +---------------------+-------------------------+
                                 |
          START  ------------>  LIVE  ------------>  REVIEW
       invitation            exchange + proof          user's record
```

The interface should feel like a modern reading room built around one historical
voice. It must not look like a generic dark dashboard with Epictetus pasted into
the header. The portrait is large on the start screen, the warm rule identifies
grounding and commitments, and long-form serif text remains the main material.

## Product contract: do not change

```text
START
  random attributed Discourses quote
  optional Notion connect -> database choice -> disconnect
  Start Call -> token request -> connected room with microphone published

LIVE
  audible agent + live two-speaker transcript
  current grounding passages, including citation, title, text, and score
  visible tool activity + captured commitment
  listening / thinking / speaking / connecting status
  mute / unmute + End Call

REVIEW
  transcript + captured commitment -> optional automatic summary draft
  every field remains editable
  Save appears only when a Notion database was chosen
  nothing is saved until Save is pressed
  New call returns to setup and refreshes the Notion connection
```

Room errors must still return the user to setup and explain the error. Ending a
call must still create the review before disconnecting. A malformed source or
activity message may hide that panel item, never end the call. Keep all current
copy unless a shorter status label is needed to fit; do not add claims.

## Page frame

```text
DESKTOP, 1280+ VIEWPORT

  32-48 outer gap
  +--------------------------------------------------------------+
  | masthead: portrait/name + context                      status |
  |==============================================================| <- 1px rule
  |                                                              |
  |                 state-specific content                       |
  |                 max width 1180px                             |
  |                                                              |
  |--------------------------------------------------------------|
  | state-specific controls                                      |
  +--------------------------------------------------------------+

MOBILE, 320-719 VIEWPORT

  16 outer gap
  +----------------------------+
  | compact name        context |
  |============================|
  | one reading column         |
  | controls stay reachable    |
  +----------------------------+
```

- Use `min-height: 100dvh`; center a `1180px` maximum frame.
- Outer padding: `clamp(16px, 3vw, 40px)`; content gaps come from the spacing
  tokens below.
- Use rules and open space to group content. Do not add floating cards, glass,
  drop shadows, or rows of rounded pills.
- The portrait is decorative (`alt=""`) because the adjacent title names him.
- Keep every content column at `min-width: 0` so long database names and source
  text cannot force horizontal scrolling.

## State 1: start

```text
DESKTOP

  +---------------- masthead: small wordmark --------------------+
  |                                                              |
  |  PORTRAIT / 01             QUOTE                              |
  |  360-440 square            28-34px serif                      |
  |  oversized white line      citation                           |
  |  art, never in a card      ---------------- warm rule         |
  |                            short product explanation          |
  |                            [ Start Call ]                      |
  |                            Notion setup / connection           |
  +--------------------------------------------------------------+

MOBILE

  name -> portrait (220-280) -> quote -> explanation -> Start Call
       -> Notion setup -> inline error
```

Hierarchy and layout:

1. The start screen is a `5 / 7` column split above `960px`, aligned around the
   quote rather than vertically centered by accident.
2. Show the approved white-line portrait at `clamp(280px, 32vw, 440px)`. It may
   crop slightly at the lower edge, but the face, hair, and beard must remain
   complete. Give it room; do not put it back into an `88px` badge here.
3. Put a quiet `01 / A conversation` index above the quote. This is metadata,
   not a badge.
4. Keep the quote and citation together. Use the warm vertical rule to connect
   the quote, explanation, and primary action into one reading column.
5. The primary action follows the explanation immediately. It must be the only
   filled control on the screen.
6. Notion is visibly optional and sits after the call action, separated by a
   hairline and the heading `Save the record`. Its connection state, database
   choice, and disconnect action keep their current behavior.
7. Place start/token and Notion errors directly under the control that can
   recover from them. Use `role="alert"`; do not use a toast.

## State 2: live call

```text
DESKTOP

  +-- compact name -------------------------------- call status --+
  |==============================================================|
  | CONVERSATION  64%        | MARGINALIA  36%                   |
  |                           |                                  |
  | You     muted serif       | WHAT HE IS DRAWING ON            |
  | Epictetus  larger serif   | 01  Book / chapter               |
  |                           |     title                         |
  | scrolls independently     |     passage + similarity         |
  |                           |                                  |
  |                           | WHAT HE IS DOING                  |
  |                           | short running activity            |
  |--------------------------------------------------------------|
  | live state + audio                         Mute     End Call   |
  +--------------------------------------------------------------+

MOBILE

  masthead -> live state -> conversation (primary, min 42dvh)
  -> grounding passages -> activity -> sticky controls
```

Hierarchy and layout:

1. Above `900px`, use a `minmax(0, 1.65fr) / minmax(300px, 0.9fr)` grid with a
   single vertical divider. Conversation is primary; proof is always visible.
2. Use the portrait at `56-64px` in the live masthead. The destination label is
   quiet metadata, not a competing call to action.
3. Transcript turns remain plain text, never chat bubbles. Speaker labels use
   compact sans text; Epictetus is `20px` and the caller is `16px` in muted ink.
   Keep `18-22px` between turns and `max-width: 42rem` for readable lines.
4. Keep automatic transcript scrolling only while the reader is already near
   the bottom. Do not obscure the transcript with controls.
5. Render sources as numbered margin notes separated by warm left rules. Keep
   citation, title, full passage, and three-decimal similarity visible. New
   source messages replace old ones exactly as they do now; an empty message
   clears stale grounding.
6. Tool activity follows sources in the same right rail. It is visually smaller
   but must be present whenever deeds exist. Commitments keep flowing into review.
7. The footer is a stable control bar. The current voice state and audio bars
   sit left; Mute and End Call sit right. End Call is outlined red, never filled
   brighter than the primary start/save actions.
8. Below `900px`, use one column. The transcript comes before evidence. The
   control bar is sticky to the bottom with a solid background and safe-area
   padding; it must not cover the last transcript or source item.

## State 3: completed review

```text
DESKTOP

  +-- Evening Review ----------------------------- call complete -+
  |==============================================================|
  |  REVIEW NOTE / guidance |  TITLE                              |
  |  New call               |  SUMMARY + draft state              |
  |                         |  NEXT STEP  <- warm rule            |
  |                         |  TRANSCRIPT                          |
  |                         |  inline error / saved state          |
  |                         |              [ Save to database ]    |
  +--------------------------------------------------------------+

MOBILE

  heading -> guidance -> title -> summary -> next step -> transcript
  -> status -> full-width Save -> New call
```

Hierarchy and layout:

1. Use a two-column editorial layout above `900px`: `220px` context rail and a
   `minmax(0, 640px)` form column. Do not turn each field into a card.
2. Keep title, summary, next step, and transcript fully editable. Inputs use the
   serif for user-written content; labels, state, and help use the sans stack.
3. Make `Next step` the visual hinge: a warm left rule and slightly raised
   surface show that it is the action carried out of the conversation. This is
   emphasis only; do not require a next step.
4. A drafting state belongs beside the Summary label and in its placeholder.
   The field stays visible and editable. If drafting fails, show the existing
   recovery message inline and keep save available.
5. Put save feedback next to the save action. After success, show a calm green
   status and keep the disabled `Saved` button visible so the result is clear.
6. With no selected database, show the existing plain explanation instead of a
   disabled or misleading Save button. `New call` remains available.
7. On mobile, Save precedes New call visually and both controls span the column.

## Type system

Use installed/system faces only; do not add a font network request.

| Token | Stack / size | Use |
|---|---|---|
| `--font-reading` | `"Iowan Old Style", "Baskerville", "Palatino Linotype", Palatino, Georgia, serif` | quote, transcript, user fields, body |
| `--font-interface` | `ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | controls, metadata, labels |
| `--type-display` | `clamp(2.5rem, 6vw, 4.75rem) / 0.98`, `-0.035em` | start title/quote emphasis only |
| `--type-quote` | `clamp(1.65rem, 3vw, 2.15rem) / 1.28`, `-0.015em` | start quote |
| `--type-agent` | `1.25rem / 1.62` | Epictetus turns |
| `--type-body` | `1rem / 1.65` | explanations, caller turns, fields |
| `--type-label` | `0.6875rem / 1.2`, `0.14em`, uppercase | section and speaker labels |
| `--type-meta` | `0.8125rem / 1.45` | citations, status, hints |

- Avoid faux old-fashioned spelling, Roman display fonts, and ornamental caps.
- Body lines should stay between roughly `45-72` characters on desktop.
- Never set source passages or editable fields below `14px`.

## Color, surface, and spacing tokens

```css
:root {
  --stone-0: #11100d; /* page */
  --stone-1: #1a1813; /* fields and sticky bars */
  --stone-2: #232018; /* active/hover surface */
  --line: #39352b;
  --line-strong: #514b3d;

  --ink: #f2eadb;
  --ink-muted: #b8ad97;
  --ink-faint: #867e6c;

  --lamp: #d8ad35;
  --lamp-bright: #f0c34a;
  --success: #7fb178;
  --thinking: #8ea4d4;
  --alarm: #d8785e;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;

  --radius-control: 4px;
  --radius-field: 6px;
}
```

- The listed text colors have verified contrast of `4.72:1` or better on the
  page background; do not lower that contrast in implementation.
- Gold means active voice, grounding, focus, or the primary action. Red means
  ending/error only. Green means speaking/saved/connected. Blue means thinking.
- Use no more than three surface values in one view. The design gets depth from
  spacing and rules, not shadows.
- Buttons are at least `44px` high. Primary buttons use gold fill, dark text,
  `4px` corners, and a small `1px` downward press. Secondary actions are quiet
  text or line buttons. Rounded capsules are reserved for small status labels.

## Interaction and motion

- Hover/focus color changes: `140ms ease-out`; screen/content entrance:
  `220ms ease-out`, opacity `0 -> 1` and vertical move no greater than `6px`.
- Do not animate width, height, large portrait movement, or scrolling panels.
- The live state dot may use one soft `1.6s` pulse while listening or thinking;
  do not pulse the whole status row. Keep LiveKit's audio bars.
- `prefers-reduced-motion: reduce` removes transforms, pulses, and smooth scroll.
  State changes must remain understandable without motion.
- Hover must never be the only signal. Pressed Mute keeps `aria-pressed` and a
  clear text change to `Unmute`.
- Preserve native text selection and scrolling. Do not intercept arrow keys,
  Escape, Tab, or browser zoom.

## Responsive, focus, and edge states

```text
>= 1100px   full asymmetric start; two-column live and review
900-1099    tighter two-column live/review; portrait at 300-340px
720-899     single-column live/review; start may retain a narrow split
< 720px     one column; 16px outer gap; full-width main actions
< 420px     compact masthead; no badge may force horizontal overflow
```

- Verify at `1440x900`, `1024x768`, `768x1024`, `390x844`, and `320x568`.
- At `200%` zoom, all actions and form fields stay reachable and readable.
- Focus order follows the visible reading order. Every link, button, select,
  input, and textarea gets a `2px --lamp-bright` `:focus-visible` outline with a
  `3px` offset. Never remove the browser focus indicator without replacing it.
- Loading:
  - Notion load: show a quiet inline `Checking Notion connection…` state in the
    Notion area; do not flash the disconnected state first.
  - Start token request: disable only the Start button and retain `Waking him…`.
  - Review draft: retain the current Summary drafting label and placeholder.
  - Review save: retain `Saving…`; do not clear form content.
- Errors use the red token, `role="alert"`, plain language, and remain in the
  same section as the failed action. No toast-only errors.
- Empty live transcript and ungrounded-source messages retain their current,
  honest explanations. The tool section stays absent until there is activity.
- An empty review remains editable. No transcript means no automatic draft;
  saving still follows the same database rule.
- Disabled controls use both lower contrast and `cursor: not-allowed`; their
  labels must still explain the current state.

## Strict evaluator contract

The evaluator must interact with the app, not grade source code or one hero
screenshot. Each cycle produces desktop and mobile screenshots plus specific
failures. A score of `8` means the bar below is met, not merely “looks good.”

### Design quality — 30%

- Start, live, and review read as stages of the same product without relying on
  identical headers alone.
- At first glance, the primary item is unmistakable: invitation/Start, live
  conversation, editable review/Save.
- Portrait, warm rule, type, surfaces, and spacing follow this contract.
- No generic dashboard cards, glass panels, gradient glow, oversized pills, or
  chat bubbles have slipped in.
- Fail at `7` or below if any state feels denser, brighter, or more generic than
  the other two, or if evidence competes with the conversation.

### Originality — 20%

- The start composition uses the line portrait as a major structural element,
  not a logo in a template.
- The live source rail clearly resembles product-specific margin evidence; the
  review carries the same rule into the next-step section.
- A screenshot with the words and portrait blurred should still have a distinct
  composition and consistent rhythm.
- Fail at `7` or below if swapping in another chatbot's name and avatar would
  leave a convincing generic assistant interface.

### Craft — 30%

- No clipping, horizontal overflow, covered content, or unreachable action at
  any required viewport or `200%` zoom.
- Keyboard-only use reaches every action in the visible order with a persistent
  focus indicator. Touch targets are at least `44px`.
- Loading, empty, disabled, error, success, hover, pressed, and reduced-motion
  states are deliberate and readable.
- Transcript and evidence scroll correctly; mobile sticky controls do not cover
  the final item; long database names wrap or truncate safely.
- Text contrast is at least `4.5:1` for normal text and `3:1` for large text and
  interface boundaries.
- Any failure above caps Craft at `7`; two or more cap it at `6`.

### Functionality — 20%

The evaluator must verify these observable paths:

1. Setup renders an attributed random quote; Start disables during admission;
   a token failure is recoverable.
2. Notion connect remains optional; connected workspace, database selection,
   empty database list, busy state, and disconnect remain usable.
3. A call connects with microphone published; status, transcript, source
   replacement/clearing, tool activity, mute/unmute, and End Call work.
4. Ending a call carries transcript and commitment into review and disconnects.
5. A review draft fills Summary/Next step when available; draft failure leaves
   the form editable; every field can be changed.
6. Save is offered only with a selected database; save failure is recoverable;
   success is announced and cannot create a second page from another click.
7. New call returns to setup and refreshes Notion state.

Any broken core path caps Functionality at `5`. A cosmetic pass cannot outweigh
a broken call, review, or save path.

## Pass rule

```text
weighted score = Design*.30 + Originality*.20 + Craft*.30 + Functionality*.20

PASS only when:
  weighted score >= 8.0
  AND no criterion < 7
  AND no core functionality path is broken
  AND required desktop + mobile + keyboard evidence exists
```

Stop after five cycles, or after two consecutive cycles improve the weighted
score by less than `0.2`. If a product decision is the only remaining blocker,
stop and ask; do not silently change the contract.
