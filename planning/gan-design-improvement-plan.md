# GAN Design Improvement Plan

**Date:** 2026-07-31
**Goal:** Make the Epictetus voice app feel distinctive, calm, and professionally designed across setup, live conversation, and review without breaking its working call and Notion flows.

```text
CURRENT APP + USER DIRECTION
            |
            v
+----------------------+       product and visual contract
| PLANNER              |----------------------------------+
| maps all 3 screens   |                                  |
+----------------------+                                  v
                                              +----------------------+
                                  feedback -->| GENERATOR            |
                                  |           | tests, then builds   |
                                  |           +----------+-----------+
                                  |                      |
                                  |                      v live app
                                  |           +----------------------+
                                  +-----------| STRICT EVALUATOR     |
                                              | clicks + screenshots |
                                              +----------+-----------+
                                                         |
                                       score >= target or bounded stop
                                                         |
                                                         v
                                              VERIFIED DESIGN RESULT
```

## Scope

- Preserve the product contract: spoken Epictetus call, visible grounding sources, tool activity, editable review, optional Notion save.
- Redesign all three user-visible states: start, live call, and completed review.
- Keep the existing dark, historical identity unless the preflight changes that direction.
- Carry the seven current uncommitted files into an isolated worktree before implementation; do not alter their originals on `main`.
- Prefer CSS and the existing React structure. Add components or dependencies only when the evaluator identifies a need that cannot be met cleanly in place.

## Done Means

- Start, live-call, and review screens have one coherent visual system and clear action order.
- Desktop and mobile layouts have no clipping, horizontal overflow, unreadable text, hidden controls, or broken focus states.
- Existing call, microphone, end-call, review editing, and Notion actions retain their current behavior.
- New UI behavior is covered test-first: the relevant test fails before implementation and passes afterward.
- `npm test`, type checking/build, and focused UI checks pass in the isolated worktree.
- A separate evaluator interacts with the live app and scores design quality, originality, craft, and functionality.

## GAN Loop

1. **Baseline** — capture the current screens and interaction paths at desktop and mobile sizes.
2. **Planner** — write the visual contract: page hierarchy, type, color, spacing, motion, responsive rules, states, and evaluation checklist.
3. **Red tests** — add the smallest useful UI/integration checks for changed behavior and confirm they fail before implementation.
4. **Generator** — implement one coherent pass, keeping the current product behavior intact and adding feature-tagged diagnostic logs only where behavior changes.
5. **Evaluator** — independently click through the live app, inspect screenshots, test keyboard/mobile/error states, and write scored feedback to `saved-results/`.
6. **Repeat** — generator reads the feedback file and fixes the highest-impact issues; evaluator re-tests from a fresh view.
7. **Final judge** — a separate judge defines what a strong result requires, checks the final app against that standard, and reports any remaining gap.

## Proposed Bounds

- Pass target: weighted score **8.0/10**.
- Maximum: **5 generator-evaluator cycles**.
- Early stop: two cycles with less than **0.2** weighted-score improvement, or a user-only/product decision blocks further progress.
- Default weights: design quality 30%, originality 20%, craft 30%, functionality 20%.

## Verification Record

Save a dated result in `saved-results/` with:

- baseline and final screenshots;
- per-cycle scores and evaluator findings;
- exact commands and results for tests, build, and viewport checks;
- changed files and any test level intentionally skipped;
- searches for the same layout or behavior issue elsewhere in the app;
- remaining limits, clearly separated from verified results.

## Start Gate

Implementation starts only after the user confirms the preflight choices: visual direction, screen scope, treatment of the current dirty files, loop/time bound, and whether a real paid voice-call smoke test is allowed.

## Revision — Restore Original Home (2026-07-31)

The redesigned start screen did not improve the user's experience. Restore the
pre-GAN centered home composition and compact masthead exactly, while retaining
the redesigned live-call and review screens plus the safer split call/Notion
error handling. Verify the restored desktop and mobile home against the saved
baseline before handoff.

## Release Plan — Vercel Production (2026-07-31)

```text
TESTED ISOLATED WORKTREE
          |
          v
commit only intended product files
          |
          v
link existing Vercel project
epictetus-resurrected
          |
          v
production deploy -> readiness check -> live browser canary
          |
          +---- unhealthy ----> restore previous Ready deployment
          |
          `---- healthy ------> save release evidence
```

- Keep the dirty local `main` worktree untouched; this repository has no Git
  remote or pull-request path.
- Deploy the verified `codex/gan-design-improvement` worktree directly to the
  existing Vercel production project after explicit release clearance.
- Re-run the 50-test suite, type check, production build, and diff review before
  deployment.
- Verify the production URL at desktop and mobile sizes, check the browser
  console, confirm the expected home structure, and inspect the deployment
  status.
- If the new deployment is unhealthy, restore the previous Ready production
  deployment instead of changing the dirty local `main` worktree.

### Cleared release sequence

The user explicitly chose to commit the current `main` files before release.
Commit that existing work as its own baseline, commit the verified design work,
merge the design branch into local `main`, and deploy the merged `main` tree to
Vercel production. No Git remote or connected Vercel Git repository exists, so
there is no external Git push target; direct Vercel deployment is the verified
release path.
