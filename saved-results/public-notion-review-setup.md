# Public Notion review setup

Date: 2026-07-31

## What this is for

This app lets each caller connect their own Notion workspace, share exactly one
database, complete a voice call, edit the resulting evening review, and save one
Notion page. The worker never searches Notion during the call. The app binds the
only shared database automatically and rejects grants with zero or multiple databases.

## Data path

```text
Notion OAuth → exactly one shared database → encrypted HttpOnly browser cookie
complete call → transcript + latest tagged commitment → Luna summary draft
editable review → explicit Save → one Notion page
```

The page uses the database's existing title property. Summary, next step, and
transcript are page-body blocks, so the app does not add or change database
properties.

## Required Vercel variables

```text
LIVEKIT_URL
LIVEKIT_API_KEY
LIVEKIT_API_SECRET
OPENAI_API_KEY
NOTION_OAUTH_CLIENT_ID
NOTION_OAUTH_CLIENT_SECRET
NOTION_OAUTH_REDIRECT_URI
NOTION_SESSION_SECRET
REVIEW_SESSION_SECRET
```

Create a public integration at `developers.notion.com`. Register the exact
deployed callback URL, for example:

```text
https://YOUR-DOMAIN/api/notion/callback
```

Generate `NOTION_SESSION_SECRET` with `openssl rand -base64 32`. Do not prefix
any secret with `NEXT_PUBLIC_`. Generate a separate `REVIEW_SESSION_SECRET` the
same way. The latter signs a 30-minute draft permit issued when a call starts;
the draft route also caps input size and limits repeated requests per forwarded
network address. Keep deployment-level rate limiting on for public traffic.

## Paid OpenAI call approval

The user explicitly approved the existing personal OpenAI API key for this
feature on 2026-07-31. The account email or account ID was not provided. The app
makes one `gpt-5.6-luna` Responses API request per completed call and sets
`store: false`. Estimated cost is about $0.001–$0.003 per review at the pricing
checked that day ($0.20 per million input tokens and $1.20 per million output
tokens). Tests make no paid calls.

## Verification completed

```text
web:    46 tests passed
types:  npx tsc --noEmit passed
build:  next build passed; 8 application/API routes emitted
visual: local front page inspected in the Codex browser
```

OAuth, automatic single-database binding and rejection, token refresh, OpenAI drafting, and Notion
page creation were exercised with local mock responses. This change did not
create or expand a real Notion grant, write a real Notion page, or make a paid
model call during verification.

## Reuse

1. Configure the public Notion integration and variables above.
2. Deploy the `web` directory.
3. Click **Connect Notion** and share only the target database itself. The app
   binds it automatically; reconnect if Notion exposes zero or multiple databases.
4. Complete a call, edit the review, and press **Save to ...**.
