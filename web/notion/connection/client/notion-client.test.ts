import { describe, expect, it, vi } from "vitest";

import {
  listSharedDatabases,
  requestNotion,
  selectSharedDatabase,
  type NotionCredentials,
} from "./notion-client";

const CREDENTIALS: NotionCredentials = {
  accessToken: "old-access-token",
  refreshToken: "refresh-token",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Notion connection client", () => {
  it("paginates through every shared data source", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        json({
          results: [
            { object: "page", id: "ignored-page" },
            { object: "data_source", id: "first", title: [{ plain_text: "Reviews" }] },
          ],
          has_more: true,
          next_cursor: "page-two",
        }),
      )
      .mockResolvedValueOnce(
        json({
          results: [
            { object: "data_source", id: "second", title: [{ plain_text: "Journal" }] },
          ],
          has_more: false,
          next_cursor: null,
        }),
      );

    const result = await listSharedDatabases(CREDENTIALS, fetcher);

    expect(result.databases).toEqual([
      { id: "first", name: "Reviews" },
      { id: "second", name: "Journal" },
    ]);
    expect(JSON.parse(String(fetcher.mock.calls[1][1]?.body))).toEqual({
      page_size: 100,
      start_cursor: "page-two",
    });
  });

  it("detects the database title property instead of assuming its name", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      json({
        id: "reviews-db",
        title: [{ plain_text: "Evening Reviews" }],
        properties: {
          Date: { type: "date" },
          Reflection: { type: "title" },
        },
      }),
    );

    const result = await selectSharedDatabase("reviews-db", CREDENTIALS, fetcher);

    expect(result.database).toEqual({
      id: "reviews-db",
      name: "Evening Reviews",
      titleProperty: "Reflection",
    });
  });

  it("refreshes an expired token once and retries the original request", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json({ message: "unauthorized" }, 401))
      .mockResolvedValueOnce(
        json({ access_token: "new-access", refresh_token: "new-refresh" }),
      )
      .mockResolvedValueOnce(json({ results: [] }));

    const result = await requestNotion(
      CREDENTIALS,
      "/v1/search",
      { method: "POST", body: JSON.stringify({}) },
      fetcher,
      { clientId: "client-id", clientSecret: "client-secret" },
    );

    expect(result.response.status).toBe(200);
    expect(result.credentials).toEqual({
      accessToken: "new-access",
      refreshToken: "new-refresh",
    });
    expect(fetcher.mock.calls[2][1]?.headers).toMatchObject({
      Authorization: "Bearer new-access",
    });
  });
});
