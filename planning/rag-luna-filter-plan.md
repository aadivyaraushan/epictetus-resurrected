# Luna retrieval filter plan

**Date:** 2026-07-31  
**Goal:** Ground the substantive turns in the supplied conversation while leaving its closing acknowledgment ungrounded.

```text
current user turn
       |
       v
hybrid search -> best cosine
       |
       +-- below 0.2315 ----------> no sources
       |
       +-- 0.2315 to below 0.36 --> GPT-5.6 Luna
       |                                |
       |                                +-- substantive --> retrieved passages
       |                                +-- acknowledgment --> no sources
       |                                +-- production error --> log + no sources
       |                                +-- dev/test error ---> raise visibly
       |
       +-- 0.36 or above ---------> retrieved passages
```

## Observable result

- Turns 1, 2, 3, 5, and 6 from the supplied transcript reach the new range and may be grounded; Turn 4 may be grounded.
- Turn 7, the acknowledgment and sign-off, is rejected by Luna and leaves the existing source panel empty.
- Luna is never called below `0.2315` or at/above `0.36`.
- A production Luna timeout or error is fully logged and publishes an empty source list. The same failure stops a development or test request with an explicit error.
- The public Vercel page keeps its current empty-source display. No frontend code or Vercel deployment is needed because the decision and source event come from the LiveKit worker.

## Build and prove

1. Create an isolated `codex/` git worktree from the current `main`; leave the existing untracked investigation files in the main checkout untouched.
2. Write failing unit and integration tests first for both score boundaries, Luna accept/reject, the Turn 7 context shape, production error logging with an empty source event, and development fail-loud behavior.
3. Add one small asynchronous GPT-5.6 Luna classifier using the existing OpenAI client dependency and Responses API. Send only the preceding Epictetus reply plus the current user turn, request one structured boolean, use no reasoning, and apply a short timeout.
4. Change the cosine floor from `0.36` to `0.2315`, while retaining `0.36` as the upper edge of the Luna-only range. Add filtered logs for the score path, Luna decision, latency, and full error context without logging full conversation text or credentials.
5. Re-run focused tests, the complete Python suite, formatting/static checks, and the existing retrieval evaluation. Search the repo for every use of the old threshold and every caller of the grounding hook; update stale documentation and tests that describe the old behavior.
6. Run a small paid classifier check against the seven supplied turns and the existing small-talk controls. Record decisions, latency, and token use when the API reports it; do not tune against unrelated examples.
7. Have a separate judge check the final behavior and evidence against the requested result. Fix any concrete failure and re-run the affected checks.
8. Deploy the worker to LiveKit Cloud, wait for the new version to become ready, and inspect privacy-safe production logs. Verify the Vercel URL and token route still respond, then make one production retrieval check by driving the app.
9. Save the final measurements, deployment version, rollback version, and reproduction commands in `saved-results/`.
