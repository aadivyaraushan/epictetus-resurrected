import { NextResponse } from "next/server";

import { openNotionSession, sealNotionSession, type NotionSession } from "../session/session";

export const NOTION_SESSION_COOKIE = "notion_session";
export const NOTION_STATE_COOKIE = "notion_oauth_state";

const COOKIE_OPTIONS = {
  httpOnly: true,
  sameSite: "lax" as const,
  secure: process.env.NODE_ENV === "production",
  path: "/",
};

export function readCookie(request: Request, name: string) {
  const cookies = request.headers.get("cookie") ?? "";
  const item = cookies.split(";").find((part) => part.trim().startsWith(`${name}=`));
  return item ? decodeURIComponent(item.trim().slice(name.length + 1)) : undefined;
}

export function notionSessionFrom(request: Request) {
  const secret = process.env.NOTION_SESSION_SECRET;
  const value = readCookie(request, NOTION_SESSION_COOKIE);
  if (!secret || !value) return null;
  return openNotionSession(value, secret);
}

export function storeNotionSession(response: NextResponse, session: NotionSession) {
  const secret = process.env.NOTION_SESSION_SECRET;
  if (!secret) throw new Error("NOTION_SESSION_SECRET is missing.");
  response.cookies.set({
    name: NOTION_SESSION_COOKIE,
    value: sealNotionSession(session, secret),
    ...COOKIE_OPTIONS,
    maxAge: 60 * 60 * 24 * 90,
  });
}

export function clearNotionSession(response: NextResponse) {
  response.cookies.set({
    name: NOTION_SESSION_COOKIE,
    value: "",
    ...COOKIE_OPTIONS,
    maxAge: 0,
  });
}

export function stateCookieOptions() {
  return { ...COOKIE_OPTIONS, maxAge: 60 * 10 };
}
