# Single Notion Review Database

Date: 2026-07-31

## Flow

```text
Connect Notion
      |
      v
Search databases visible to this OAuth connection
      |
      +-- 0 databases ------> reject + reconnect with the original database
      |
      +-- 1 database -------> validate title field + save it in the session
      |
      +-- 2+ databases -----> reject + reconnect while sharing only one
```

## Done means

- The start screen never shows a database dropdown.
- A connection with exactly one visible database stores that database automatically.
- Zero or multiple visible databases leave the connection unusable and show a clear reconnect action.
- Existing encrypted cookie storage, token refresh, disconnect, and review saving still work.

## Steps

1. Add failing route and start-screen tests for the three database-count cases and the removed dropdown.
2. Move the one-database decision into the Notion status route and store the automatic selection.
3. Replace the dropdown with the bound database name or reconnect guidance.
4. Search for old database-selection callers and remove the replaced path.
5. Run focused tests, the full web test suite, TypeScript, and the production build.
6. Inspect the screen in the browser and have an independent judge review the result.

## Boundaries

- Do not touch the user's original dirty checkout.
- Do not grant Notion access to any additional page.
- Do not expose OAuth or session secrets.
