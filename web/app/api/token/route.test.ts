/**
 * What the token endpoint actually signs.
 *
 * These run the real route handler and then verify the token it returns with the
 * same secret LiveKit would use. No browser input should select a private data
 * backend or become trusted participant metadata.
 *
 * No network: minting and verifying a token is local signing, so this costs
 * nothing and runs in milliseconds.
 */

import { TokenVerifier } from "livekit-server-sdk";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { POST } from "./route";

const KEY = "APItestkey";
const SECRET = "a-test-secret-long-enough-to-sign-with";
function ask(body: unknown = {}) {
  return POST(
    new Request("http://localhost/api/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

async function claimsIn(token: string) {
  return new TokenVerifier(KEY, SECRET).verify(token);
}

let saved: Record<string, string | undefined>;

beforeEach(() => {
  saved = { ...process.env };
  process.env.LIVEKIT_URL = "wss://example.livekit.cloud";
  process.env.LIVEKIT_API_KEY = KEY;
  process.env.LIVEKIT_API_SECRET = SECRET;
  process.env.REVIEW_SESSION_SECRET = "review-session-secret";
});

afterEach(() => {
  process.env = saved as NodeJS.ProcessEnv;
});

describe("POST /api/token", () => {
  it("does not sign a private backend into a caller token", async () => {
    const body = await (await ask({})).json();
    expect(body.backend).toBeUndefined();

    const claims = await claimsIn(body.token);
    expect(claims.metadata).toBeFalsy();
  });

  it("ignores old passphrase and metadata fields", async () => {
    const body = await (
      await ask({ passphrase: "old-secret", metadata: JSON.stringify({ life_backend: "live" }) })
    ).json();

    const claims = await claimsIn(body.token);
    expect(claims.metadata).toBeFalsy();
  });

  it("scopes the token to one room, and to that room only", async () => {
    const first = await (await ask({})).json();
    const second = await (await ask({})).json();
    expect(first.roomName).not.toBe(second.roomName);

    const claims = await claimsIn(first.token);
    expect(claims.video?.room).toBe(first.roomName);
    expect(claims.video?.roomJoin).toBe(true);
    expect(claims.video?.canPublish).toBe(true);
    // Nothing that would let a caller reach past their own call.
    expect(claims.video?.roomCreate).toBeFalsy();
    expect(claims.video?.roomAdmin).toBeFalsy();
    expect(claims.video?.roomList).toBeFalsy();
  });

  // The worker registers under a name, which means LiveKit will not send it into
  // a room unless a token asks for it by that name. Read the field rather than
  // searching the token for the string "epictetus" -- the room name contains
  // that too, so a looser check passes even with the dispatch missing entirely.
  it("asks LiveKit to dispatch the worker by name", async () => {
    const body = await (await ask({})).json();
    const claims = await claimsIn(body.token);
    const agents = (claims.roomConfig as { agents?: { agentName?: string }[] })?.agents;
    expect(agents?.map((agent) => agent.agentName)).toEqual(["epictetus"]);
  });

  it("returns the server URL the browser should connect to", async () => {
    const body = await (await ask({})).json();
    expect(body.serverUrl).toBe("wss://example.livekit.cloud");
  });

  it("issues a short-lived HttpOnly permit for one review draft", async () => {
    const response = await ask();
    expect(response.headers.get("set-cookie")).toContain("review_permit=");
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  });

  it("survives a body that is not JSON at all", async () => {
    const response = await POST(
      new Request("http://localhost/api/token", { method: "POST", body: "not json" }),
    );
    const body = await response.json();
    expect(response.status).toBe(200);
  });

  it("refuses to mint anything when the server is not configured", async () => {
    delete process.env.LIVEKIT_API_SECRET;
    const response = await ask({});
    expect(response.status).toBe(500);
    expect((await response.json()).error).toContain("LIVEKIT_API_SECRET");
  });

});
