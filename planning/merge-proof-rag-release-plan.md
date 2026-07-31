# Proof Dashboard + RAG Release Plan

**Date:** 2026-08-01

```text
main + RAG/review branch + proof-dashboard branch
                         |
                         v
              combined release worktree
                         |
              tests + browser checks + judge
                         |
             +-----------+-----------+
             |                       |
        Vercel frontend         LiveKit worker
        `/` and `/proof`        combined RAG events
```

## Done

- `/` keeps the current call, chapter evidence, and review draft behavior.
- `/proof` is live and shows safe room, transcript, RAG, and tool events.
- Each RAG event accurately names the score path and Luna decision.
- The same merged commit is deployed to Vercel and LiveKit Cloud.

## Checks

1. Write combined contract tests before merging the proof commit.
2. Merge both branches with normal Git history and resolve shared files.
3. Run focused and full Python/web checks plus the production build.
4. Inspect `/` and `/proof` locally at desktop and mobile sizes.
5. Have a fresh judge check the finished release against both source tasks.
6. Record rollback versions, deploy both services, and verify one real call.

## Boundaries

- Preserve the dirty main checkout and the original source worktrees.
- Keep secrets out of files and browser-visible events.
- Keep `0.2315`, `0.36`, and Luna `high` reasoning unchanged.
