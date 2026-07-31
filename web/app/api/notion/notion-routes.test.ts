import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET as beginOAuth } from "./connect/route";
import { GET as finishOAuth } from "./callback/route";
import { DELETE, GET, POST } from "./route";

function cookieFrom(response: Response, name: string) {
  const match = response.headers.get("set-cookie")?.match(new RegExp(`${name}=([^;,]+)`));
  return match?.[1] ?? "";
}

let saved: NodeJS.ProcessEnv;

beforeEach(() => {
  saved = { ...process.env };
  process.env.NOTION_OAUTH_CLIENT_ID = "client-id";
  process.env.NOTION_OAUTH_CLIENT_SECRET = "client-secret";
  process.env.NOTION_OAUTH_REDIRECT_URI = "http://localhost:3000/api/notion/callback";
  process.env.NOTION_SESSION_SECRET = "a-long-session-secret";
});

afterEach(() => {
  process.env = saved;
  vi.unstubAllGlobals();
});

describe("public Notion connection routes", () => {
  it("starts OAuth with a CSRF state stored in an HttpOnly cookie", async () => {
    const response = await beginOAuth(new Request("http://localhost:3000/api/notion/connect"));
    const location = new URL(response.headers.get("location")!);

    expect(location.origin + location.pathname).toBe("https://api.notion.com/v1/oauth/authorize");
    expect(location.searchParams.get("client_id")).toBe("client-id");
    expect(location.searchParams.get("redirect_uri")).toBe(process.env.NOTION_OAUTH_REDIRECT_URI);
    expect(location.searchParams.get("state")).toBeTruthy();
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  });

  it("exchanges a valid callback and stores an encrypted browser session", async () => {
    const start = await beginOAuth(new Request("http://localhost:3000/api/notion/connect"));
    const state = new URL(start.headers.get("location")!).searchParams.get("state")!;
    const stateCookie = cookieFrom(start, "notion_oauth_state");
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "notion-access",
          refresh_token: "notion-refresh",
          workspace_name: "My Workspace",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetcher);

    const response = await finishOAuth(
      new Request(`http://localhost:3000/api/notion/callback?code=oauth-code&state=${state}`, {
        headers: { Cookie: `notion_oauth_state=${stateCookie}` },
      }),
    );

    const sessionCookie = cookieFrom(response, "notion_session");
    expect(response.headers.get("location")).toBe("http://localhost:3000/?notion=connected");
    expect(sessionCookie).toBeTruthy();
    expect(sessionCookie).not.toContain("notion-access");
  });

  it("rejects a callback whose state does not match the browser", async () => {
    const response = await finishOAuth(
      new Request("http://localhost:3000/api/notion/callback?code=code&state=wrong", {
        headers: { Cookie: "notion_oauth_state=expected" },
      }),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/?notion=error&notion_error=Notion+authorization+was+cancelled+or+invalid.",
    );
  });

  it("lists accessible databases, selects one, and remembers it", async () => {
    const start = await beginOAuth(new Request("http://localhost:3000/api/notion/connect"));
    const state = new URL(start.headers.get("location")!).searchParams.get("state")!;
    const stateCookie = cookieFrom(start, "notion_oauth_state");
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              access_token: "notion-access",
              refresh_token: "notion-refresh",
              workspace_name: "My Workspace",
            }),
            { status: 200 },
          ),
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              results: [
                { object: "data_source", id: "reviews", title: [{ plain_text: "Reviews" }] },
              ],
              has_more: false,
            }),
            { status: 200 },
          ),
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              id: "reviews",
              title: [{ plain_text: "Reviews" }],
              properties: { Reflection: { type: "title" } },
            }),
            { status: 200 },
          ),
        ),
    );
    const callback = await finishOAuth(
      new Request(`http://localhost:3000/api/notion/callback?code=code&state=${state}`, {
        headers: { Cookie: `notion_oauth_state=${stateCookie}` },
      }),
    );
    const sessionCookie = cookieFrom(callback, "notion_session");

    const status = await GET(
      new Request("http://localhost:3000/api/notion", {
        headers: { Cookie: `notion_session=${sessionCookie}` },
      }),
    );
    expect(await status.json()).toMatchObject({
      connected: true,
      workspaceName: "My Workspace",
      databases: [{ id: "reviews", name: "Reviews" }],
    });

    const selection = await POST(
      new Request("http://localhost:3000/api/notion", {
        method: "POST",
        headers: {
          Cookie: `notion_session=${sessionCookie}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ dataSourceId: "reviews" }),
      }),
    );
    expect(await selection.json()).toMatchObject({
      selectedDatabase: { id: "reviews", name: "Reviews", titleProperty: "Reflection" },
    });
    expect(cookieFrom(selection, "notion_session")).toBeTruthy();
  });

  it("disconnects by clearing the browser session", async () => {
    const response = await DELETE();
    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toContain("notion_session=");
  });
});
