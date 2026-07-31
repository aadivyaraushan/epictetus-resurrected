import { randomBytes } from "node:crypto";
import { NextResponse } from "next/server";

import {
  NOTION_STATE_COOKIE,
  stateCookieOptions,
} from "../../../../notion/connection/cookie/session-cookie";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_request: Request) {
  const clientId = process.env.NOTION_OAUTH_CLIENT_ID;
  const redirectUri = process.env.NOTION_OAUTH_REDIRECT_URI;
  if (!clientId || !redirectUri) {
    console.error("[notion.oauth] cannot begin; OAuth client configuration is incomplete");
    return NextResponse.json({ error: "Notion connection is not configured." }, { status: 500 });
  }

  const state = randomBytes(24).toString("base64url");
  const url = new URL("https://api.notion.com/v1/oauth/authorize");
  url.searchParams.set("owner", "user");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("state", state);

  const response = NextResponse.redirect(url);
  response.cookies.set({
    name: NOTION_STATE_COOKIE,
    value: state,
    ...stateCookieOptions(),
  });
  console.info("[notion.oauth] authorization started");
  return response;
}
