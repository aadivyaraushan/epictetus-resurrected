# Automatic review draft fix

Date: 2026-08-01

## Cause

The first production failure was caused by a missing `OPENAI_API_KEY` in Vercel Production. After adding the encrypted variable, the request reached OpenAI but returned HTTP 400 because `gpt-5.6-luna` does not accept `reasoning.effort: "minimal"`.

The provider error listed `none`, `low`, `medium`, `high`, `xhigh`, and `max` as supported values. The request now uses `high`.

## Change

- Added the existing local key to Vercel Production without writing it to the repository.
- Changed `web/review/draft/openai-review.ts` to send `reasoning: { effort: "high" }`.
- Added a regression assertion in `web/review/draft/openai-review.test.ts`.

## Verification

- Deployment: `dpl_5RLHczRmA11DR1WwAuntstGP1ewU`
- Production state: Ready
- Direct production request: HTTP 200, returned summary and next step
- Browser call: summary filled, no automatic-draft failure, no browser errors
- Vercel log: `produced summary_chars=124 next_step=false`
- Web tests: 56/56 passed
- Production build: passed

## Reproduce

From the isolated worktree:

```bash
npm test
npm run build
```

The live endpoint is `/api/review/draft`; it requires the review permit cookie issued by `/api/token`.
