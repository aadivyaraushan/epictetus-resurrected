# Public Notion Reviews and Rotating Quotes

Date: 2026-07-31

## What ships

```text
FRONT PAGE
  curated Discourses quotes ──random pick──> one quote per page visit

NOTION SETUP
  Connect Notion ──OAuth──> choose a shared database ──> encrypted browser cookie
                                                           (server-readable only)

CALL
  live transcript ───────────────┐
  tagged user commitment ────────┼──> End Call ──> editable review
                                 │                 ├─ transcript
                                 └─ OpenAI draft ──┼─ summary
                                                   └─ next step
                                                          │
                                                          └──> one Notion page
```

The private passphrase, author-only Notion credentials, live note search, and
fixed journal page are removed. A call can still run without Notion; saving the
finished review requires a connected database.

## User-visible contract

- A verified Discourses quote and citation are randomly selected when the front
  page loads.
- **Connect Notion** uses Notion OAuth. The user chooses from databases shared
  during authorization. The same browser remembers the encrypted connection.
- Ending a call opens a review screen instead of discarding the transcript.
- The review contains editable transcript, auto-drafted summary, and next step.
- The latest commitment captured by the existing session-log behavior is used
  as the next-step draft. If none was captured, the drafting call may fill it
  only from an explicit commitment in the transcript; otherwise it stays blank.
- **Save to Notion** creates one page in the selected data source. The existing
  title property receives a dated title; the three review sections live in the
  page body, so no custom database schema is required.
- Tokens never enter browser JavaScript, LiveKit participant metadata, logs, or
  source control. OAuth and database selection live in an encrypted, HttpOnly,
  same-site cookie on the same browser.

## Implementation map

```text
web/call/start-screen/       quote set, random picker, Notion setup controls
web/notion/connection/       Notion HTTP client + encrypted cookie session
web/app/api/notion/          connect, callback, list/select, disconnect routes
web/call/live/               lift transcript + tagged commitment to page state
web/call/review/             editable completed-review screen
web/app/api/review/          OpenAI draft route + Notion save route
agent/persona/               tag running-log entries; remove Notion read/write
agent/tools/personal/        delete the private/demo backend switch
```

## Build order and checks

1. Write quote-picker tests, run them red, then add the curated set and picker.
2. Write OAuth state, encrypted-cookie, database-list/selection, and save-request
   tests; run red; then implement against Notion API version `2026-03-11`.
3. Write agent tests for tagged commitments and the removed Notion tools; run
   red; then simplify the worker to an in-call record only.
4. Write transcript handoff, review drafting, review editing, and save-flow tests;
   run red; then implement the review screen and API routes.
5. Add tagged logs at boundaries: OAuth result, database choice, draft input
   size/result, save result, and caught errors. Never log tokens or transcript
   contents.
6. Search for every old passphrase, live backend, fixed Notion page, and Notion
   search reference; remove or update all callers and documentation.
7. Run Python tests, web tests, type/build checks, then inspect desktop and mobile
   flows in the browser. OAuth itself uses mocked HTTP responses; no paid model
   call or real Notion write is needed for verification.
8. Give the finished diff to a fresh judge agent. Fix any requirement, security,
   accessibility, or evidence gap it finds, then rerun affected checks.

## External setup after code

- Create a Notion public connection with read-content and insert-content access,
  an OAuth callback URL, and installation scope **Any workspace**.
- Configure `NOTION_OAUTH_CLIENT_ID`, `NOTION_OAUTH_CLIENT_SECRET`,
  `NOTION_OAUTH_REDIRECT_URI`, `NOTION_SESSION_SECRET`, `REVIEW_SESSION_SECRET`,
  and `OPENAI_API_KEY` in Vercel. Keep the existing worker key for the live
  conversation model.
- Approved paid account: the user's personal OpenAI account; email/account ID
  was not provided. Approval was explicit on 2026-07-31. Estimated added cost:
  about $0.001-$0.003 per completed review using `gpt-5.6-luna`.

## Stop conditions

- Do not make a real paid OpenAI call or write to a real Notion workspace while
  testing.
- Do not deploy, upload secrets, or configure the Notion developer portal in
  this implementation turn.
- Do not touch the original checkout's uncommitted files.

## Result

- [x] 16 source-checked quotes across all four books; one random choice per load.
- [x] Public Notion OAuth, encrypted same-browser session, token refresh, and
  database selection.
- [x] Private passphrase, fixed author pages, and in-call Notion search removed.
- [x] Existing session log now tags commitments; latest commitment feeds the
  editable next-step field.
- [x] Completed-call review screen with transcript, Luna summary draft, and one
  explicit Notion page save.
- [x] Full-length commitment handoff plus a short-lived paid-draft permit, input
  caps, and per-address throttling.
- [x] Mocked integration tests, complete web/worker suites, TypeScript, production
  build, and Chrome visual checks passed without paid calls or real Notion writes.
