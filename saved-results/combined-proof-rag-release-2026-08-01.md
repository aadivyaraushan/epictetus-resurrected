# Combined Proof + RAG Production Release

**Date:** 2026-08-01
**Purpose:** Preserve the exact merged release, verification evidence, live
deployment identifiers, and rollback steps for the proof dashboard, repaired
Epictetus retrieval flow, review draft, and GPT-5.6 Luna voice worker.

## Result

- Production runtime commit: `73fc4ced83ea5e7d6fb2912d705af75321990d86`.
- Public app: `https://epictetus-resurrected.vercel.app`.
- Hidden recording view: `https://epictetus-resurrected.vercel.app/proof`.
- Vercel production: `dpl_71mLapYUSfKc6vXB2m2R6f7LUYoo`, Ready.
- LiveKit production: `ynTAeumzVE3r`, Available, current, active, and tagged
  with Git commit `73fc4ce` on `codex/merge-proof-rag-release`.

## What was merged

- RAG and review history from `codex/rag-luna-filter`.
- Recording-only `/proof` dashboard from `codex/proof-call-dashboard`.
- GPT-5.6 Luna voice worker from commit `eeb2bd7`.
- Review fixes from the independent release judge: show the exact `0.2315`
  floor and wait for LiveKit `onConnected` before recording room admission.

## Verification

- TDD red run: 5 Python contract failures before RAG proof events existed; 3
  web contract failures before the shared `/proof` experience existed; then 2
  focused web failures reproduced the rounded floor and early-admission bugs.
- Final Python suite: 66 tests passed.
- Final web suite: 67 tests passed across 16 files.
- Ruff on `agent` and `tests`: passed.
- TypeScript: passed with `npx tsc --noEmit`.
- Next production build: passed and emitted both `/` and `/proof`.
- Independent Sol judge: `SHIP` for clean production commit `73fc4ce`.
- Production Playwright smoke: `/` returned 200, `/proof` returned 200, and
  both rendered `Epictetus, Resurrected`.

## Real production call

Playwright Chromium used a fake microphone WAV with three spoken requests: an
Epictetus question about anger and control, a request to write a commitment to
the session log, and a request to look up the first iPhone release year.

Observed in one `/proof` call:

- LiveKit room admission appeared only after connection.
- Remote audio was attached and playing (`paused=false`, `muted=false`,
  `readyState=4`, `hasStream=true`).
- Three RAG decisions appeared and each displayed `minimum 0.2315` and
  `automatic at 0.360`.
- `writing in the session log` fired with the captured commitment.
- `looking up` fired for the first iPhone release year.
- The completed review drafted a 259-character summary, retained the captured
  next step, kept a 1,026-character transcript, and listed seven referenced
  chapters. No browser or review error was recorded.
- Notion save was not part of this browser run because the fresh browser had no
  connected Notion session. The seven Notion route tests passed in the final
  67-test web suite.

Evidence:

- `saved-results/combined-proof-rag-release/production-live-evidence.json`
- `saved-results/combined-proof-rag-release/production-proof-live.png`
- `saved-results/combined-proof-rag-release/production-review-live.png`

## Rollback

Previous versions were preserved:

- Vercel: `dpl_5RLHczRmA11DR1WwAuntstGP1ewU`.
- LiveKit: `fEHe7zJqJHSA`.

The installed CLIs confirmed these command forms without executing them:

```bash
cd web
vercel rollback dpl_5RLHczRmA11DR1WwAuntstGP1ewU --yes

cd ..
lk agent rollback --version fEHe7zJqJHSA .
```

## Dependency audit note

`npm audit --omit=dev` reports three high findings through Next's `postcss` and
optional `sharp` dependencies. The judge found no first-party attacker-controlled
CSS, source-map, image upload, `next/image`, or remote-image path. The suggested
automatic fix is a breaking downgrade to Next 9, so it was not applied. Track
the findings until Next supplies patched dependencies.

## Reuse

To repeat the safe checks without a paid call:

```bash
pytest -q
cd web
npm test -- --run
npx tsc --noEmit
npm run build
```

For a new production release, record the current Vercel and LiveKit versions,
deploy one clean Git commit to both services, and repeat the real `/proof` call.
