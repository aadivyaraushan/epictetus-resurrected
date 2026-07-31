import { timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";

import {
  NOTION_STATE_COOKIE,
  readCookie,
  stateCookieOptions,
  storeNotionSession,
} from "../../../../notion/connection/cookie/session-cookie";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function statesMatch(received: string, expected: string) {
  const left = Buffer.from(received);
  const right = Buffer.from(expected);
  return left.length === right.length && timingSafeEqual(left, right);
}

function returnToAppWithError(request: Request, message: string) {
  const destination = new URL("/", request.url);
  destination.searchParams.set("notion", "error");
  destination.searchParams.set("notion_error", message);
  return NextResponse.redirect(destination);
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code") ?? "";
  const receivedState = url.searchParams.get("state") ?? "";
  const expectedState = readCookie(request, NOTION_STATE_COOKIE) ?? "";
  if (!code || !receivedState || !expectedState || !statesMatch(receivedState, expectedState)) {
    console.warn("[notion.oauth] callback rejected; missing code or state mismatch");
    return returnToAppWithError(
      request,
      "Notion authorization was cancelled or invalid.",
    );
  }

  const clientId = process.env.NOTION_OAUTH_CLIENT_ID;
  const clientSecret = process.env.NOTION_OAUTH_CLIENT_SECRET;
  const redirectUri = process.env.NOTION_OAUTH_REDIRECT_URI;
  if (!clientId || !clientSecret || !redirectUri || !process.env.NOTION_SESSION_SECRET) {
    console.error("[notion.oauth] callback cannot finish; server configuration is incomplete");
    return NextResponse.json({ error: "Notion connection is not configured." }, { status: 500 });
  }

  try {
    const tokenResponse = await fetch("https://api.notion.com/v1/oauth/token", {
      method: "POST",
      headers: {
        Authorization: `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString("base64")}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        grant_type: "authorization_code",
        code,
        redirect_uri: redirectUri,
      }),
    });
    if (!tokenResponse.ok) throw new Error(`token exchange returned ${tokenResponse.status}`);
    const token = (await tokenResponse.json()) as {
      access_token?: string;
      refresh_token?: string;
      workspace_name?: string | null;
    };
    if (!token.access_token || !token.refresh_token) {
      throw new Error("token exchange returned incomplete credentials");
    }

    const response = NextResponse.redirect(new URL("/?notion=connected", request.url));
    storeNotionSession(response, {
      accessToken: token.access_token,
      refreshToken: token.refresh_token,
      workspaceName: token.workspace_name?.trim() || "Notion workspace",
    });
    response.cookies.set({
      name: NOTION_STATE_COOKIE,
      value: "",
      ...stateCookieOptions(),
      maxAge: 0,
    });
    console.info("[notion.oauth] workspace connected");
    return response;
  } catch (error) {
    console.error("[notion.oauth] callback failed", error);
    return returnToAppWithError(request, "Could not connect Notion. Please try again.");
  }
}
