# Merge GAN Design and Single-Database Notion Fix

**Date:** 2026-07-31
**Goal:** Deploy one production build that keeps the approved GAN live-call and review design while also keeping the single-database Notion connection behavior.

```text
main @ cee47e1                          Notion fix @ 9099eca
GAN design + public Notion flow        bind exactly one shared database
             \                         /
              \                       /
               v                     v
          isolated merge worktree and branch
                         |
                         v
       focused tests -> full tests -> types -> build
                         |
                         v
              direct Vercel production deploy
                         |
             +-----------+-----------+
             |                       |
       live checks pass          live checks fail
             |                       |
             v                       v
       save evidence        restore previous Ready deploy
```

## Verified Starting State

- Local `main` is clean at `cee47e1` and includes the GAN design merge `13bd0d6`.
- The single-database Notion fix is commit `9099eca`, based on the common ancestor `bdc4700`.
- The repository has no Git remote, so the release path is a local merge plus a direct deploy to the linked Vercel project `epictetus-resurrected`.
- The current production mismatch came from promoting separate builds: the known-good Notion build has the old design, while the newer design build does not include `9099eca`.

## Steps

1. Create a new isolated Git worktree and branch from `main`; leave the primary checkout and existing feature worktrees unchanged.
2. Bring commit `9099eca` into the new branch with a normal merge so both histories remain visible.
3. Review every overlapping file, preserving the GAN visual structure and the Notion rule that exactly one shared database is bound automatically with no dropdown.
4. Reuse the existing regression tests from `9099eca`. If conflict resolution changes behavior, add or adjust the failing combined-behavior test before changing product code.
5. Run the focused Notion and start-screen tests, the full web suite, TypeScript checking, and the production build.
6. Search the repository for the removed database-selection API and dropdown behavior; fix any remaining caller that still depends on the old contract.
7. Have a separate judge inspect the merged diff and test evidence against the requested combined result.
8. Deploy the verified worktree directly to the existing Vercel Production project, keeping the previous Ready deployment available for rollback.
9. Verify the stable URL on desktop and mobile: approved home/live/review design, no database dropdown, working Connect Notion redirect to the consent screen, HTTP success, no console errors, no horizontal overflow, and a successful `/api/token` smoke check without printing its token or cookie.
10. Save the merge and deployment evidence under `saved-results/` and `.gstack/deploy-reports/`.

## Done Means

- Production shows the approved GAN design and never shows an “Untitled database” selector.
- Connect Notion reaches the real Notion consent screen without granting workspace access during verification.
- A single shared database is bound automatically; zero or multiple databases require reconnecting.
- Focused tests, full tests, TypeScript, local build, Vercel build, and live browser checks pass in this run.
- The merged commit, production deployment ID, live evidence, and rollback source are recorded.

## Safety Boundaries

- Do not expose or replace existing secrets.
- Do not grant Notion access or write a Notion page during the canary.
- Do not start a paid voice call.
- Do not create a Git remote, force-push, or modify unrelated worktrees.
- If production checks fail, restore the previous Ready deployment before debugging further.
