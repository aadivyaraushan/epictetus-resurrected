import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST as draft } from "./draft/route";
import { POST as save } from "./save/route";
import { sealNotionSession } from "../../../notion/connection/session/session";
import { createReviewPermit } from "../../../review/draft/access/review-access";

let saved: NodeJS.ProcessEnv;

beforeEach(() => {
  saved = { ...process.env };
  process.env.OPENAI_API_KEY = "test-openai-key";
  process.env.NOTION_SESSION_SECRET = "a-long-session-secret";
  process.env.NOTION_OAUTH_CLIENT_ID = "client-id";
  process.env.NOTION_OAUTH_CLIENT_SECRET = "client-secret";
  process.env.REVIEW_SESSION_SECRET = "review-session-secret";
});

afterEach(() => {
  process.env = saved;
  vi.unstubAllGlobals();
});

describe("completed review routes", () => {
  it("drafts the editable summary without making the review completed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: "completed",
            output: [
              {
                type: "message",
                content: [
                  {
                    type: "output_text",
                    text: JSON.stringify({ summary: "A summary.", explicitNextStep: "" }),
                  },
                ],
              },
            ],
          }),
          { status: 200 },
        ),
      ),
    );
    const permit = createReviewPermit(process.env.REVIEW_SESSION_SECRET!);
    const response = await draft(
      new Request("http://localhost:3000/api/review/draft", {
        method: "POST",
        headers: { Cookie: `review_permit=${permit}`, "x-forwarded-for": "203.0.113.10" },
        body: JSON.stringify({ transcript: "You: A reflection.", capturedCommitment: "" }),
      }),
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ summary: "A summary.", nextStep: "" });
    expect(response.headers.get("set-cookie")).toContain("review_permit=");
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
  });

  it("rejects an oversized transcript before calling OpenAI", async () => {
    const fetcher = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetcher);
    const permit = createReviewPermit(process.env.REVIEW_SESSION_SECRET!);

    const response = await draft(
      new Request("http://localhost:3000/api/review/draft", {
        method: "POST",
        headers: { Cookie: `review_permit=${permit}`, "x-forwarded-for": "203.0.113.11" },
        body: JSON.stringify({ transcript: "x".repeat(60_001), capturedCommitment: "" }),
      }),
    );

    expect(response.status).toBe(413);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("rejects a draft without a server-issued call permit", async () => {
    const response = await draft(
      new Request("http://localhost:3000/api/review/draft", {
        method: "POST",
        body: JSON.stringify({ transcript: "You: A reflection.", capturedCommitment: "" }),
      }),
    );

    expect(response.status).toBe(401);
  });

  it("rejects an oversized captured commitment before calling OpenAI", async () => {
    const fetcher = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetcher);
    const permit = createReviewPermit(process.env.REVIEW_SESSION_SECRET!);
    const response = await draft(
      new Request("http://localhost:3000/api/review/draft", {
        method: "POST",
        headers: { Cookie: `review_permit=${permit}`, "x-forwarded-for": "203.0.113.12" },
        body: JSON.stringify({
          transcript: "You: I will do it.",
          capturedCommitment: "x".repeat(2_001),
        }),
      }),
    );

    expect(response.status).toBe(413);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("refuses to write an unfinished review", async () => {
    const response = await save(
      new Request("http://localhost:3000/api/review/save", {
        method: "POST",
        body: JSON.stringify({ completed: false }),
      }),
    );

    expect(response.status).toBe(400);
  });

  it("writes exactly one page only after review completion", async () => {
    const session = sealNotionSession(
      {
        accessToken: "notion-access",
        refreshToken: "notion-refresh",
        workspaceName: "My Workspace",
        selectedDatabase: {
          id: "reviews",
          name: "Evening Reviews",
          titleProperty: "Reflection",
        },
      },
      process.env.NOTION_SESSION_SECRET!,
    );
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ id: "new-page" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetcher);

    const response = await save(
      new Request("http://localhost:3000/api/review/save", {
        method: "POST",
        headers: { Cookie: `notion_session=${session}` },
        body: JSON.stringify({
          completed: true,
          title: "Evening Review — July 31, 2026",
          summary: "A summary.",
          nextStep: "Send the outline.",
          transcript: "You: I will send it.",
        }),
      }),
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ saved: true, pageId: "new-page" });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).toBe("https://api.notion.com/v1/pages");
  });
});
