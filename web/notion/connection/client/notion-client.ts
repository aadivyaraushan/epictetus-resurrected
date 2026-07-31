import type { SelectedNotionDatabase } from "../session/session";

export type NotionCredentials = {
  accessToken: string;
  refreshToken: string;
};

type OAuthClient = { clientId: string; clientSecret: string };
type RequestResult = { response: Response; credentials: NotionCredentials };

const NOTION_API = "https://api.notion.com";
const NOTION_VERSION = "2026-03-11";

function notionHeaders(accessToken: string, headers?: HeadersInit) {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
    ...headers,
  };
}

async function refreshCredentials(
  credentials: NotionCredentials,
  fetcher: typeof fetch,
  oauth: OAuthClient,
): Promise<NotionCredentials> {
  const response = await fetcher(`${NOTION_API}/v1/oauth/token`, {
    method: "POST",
    headers: {
      Authorization: `Basic ${Buffer.from(`${oauth.clientId}:${oauth.clientSecret}`).toString("base64")}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      grant_type: "refresh_token",
      refresh_token: credentials.refreshToken,
    }),
  });
  if (!response.ok) throw new Error(`Notion token refresh failed (${response.status}).`);

  const body = (await response.json()) as {
    access_token?: string;
    refresh_token?: string;
  };
  if (!body.access_token || !body.refresh_token) {
    throw new Error("Notion token refresh returned incomplete credentials.");
  }
  return { accessToken: body.access_token, refreshToken: body.refresh_token };
}

export async function requestNotion(
  credentials: NotionCredentials,
  path: string,
  init: RequestInit,
  fetcher: typeof fetch = fetch,
  oauth?: OAuthClient,
): Promise<RequestResult> {
  const send = (accessToken: string) =>
    fetcher(`${NOTION_API}${path}`, {
      ...init,
      headers: notionHeaders(accessToken, init.headers),
    });

  let response = await send(credentials.accessToken);
  if (response.status !== 401 || !oauth) return { response, credentials };

  const refreshed = await refreshCredentials(credentials, fetcher, oauth);
  response = await send(refreshed.accessToken);
  return { response, credentials: refreshed };
}

type SearchResult = {
  object?: string;
  id?: string;
  title?: { plain_text?: string }[];
};

function titleOf(item: SearchResult) {
  return item.title?.map((part) => part.plain_text ?? "").join("").trim() || "Untitled database";
}

export async function listSharedDatabases(
  credentials: NotionCredentials,
  fetcher: typeof fetch = fetch,
  oauth?: OAuthClient,
) {
  const databases: { id: string; name: string }[] = [];
  let cursor: string | null = null;
  let currentCredentials = credentials;

  do {
    const body: { page_size: number; start_cursor?: string } = { page_size: 100 };
    if (cursor) body.start_cursor = cursor;
    const result = await requestNotion(
      currentCredentials,
      "/v1/search",
      { method: "POST", body: JSON.stringify(body) },
      fetcher,
      oauth,
    );
    currentCredentials = result.credentials;
    if (!result.response.ok) {
      throw new Error(`Notion database search failed (${result.response.status}).`);
    }
    const page = (await result.response.json()) as {
      results?: SearchResult[];
      has_more?: boolean;
      next_cursor?: string | null;
    };
    for (const item of page.results ?? []) {
      if (item.object === "data_source" && item.id) {
        databases.push({ id: item.id, name: titleOf(item) });
      }
    }
    cursor = page.has_more ? (page.next_cursor ?? null) : null;
  } while (cursor);

  return { databases, credentials: currentCredentials };
}

export async function selectSharedDatabase(
  id: string,
  credentials: NotionCredentials,
  fetcher: typeof fetch = fetch,
  oauth?: OAuthClient,
) {
  const result = await requestNotion(
    credentials,
    `/v1/data_sources/${encodeURIComponent(id)}`,
    { method: "GET" },
    fetcher,
    oauth,
  );
  if (!result.response.ok) {
    throw new Error(`Notion database lookup failed (${result.response.status}).`);
  }
  const body = (await result.response.json()) as {
    id?: string;
    title?: { plain_text?: string }[];
    properties?: Record<string, { type?: string }>;
  };
  const titleProperty = Object.entries(body.properties ?? {}).find(
    ([, property]) => property.type === "title",
  )?.[0];
  if (!body.id || !titleProperty) throw new Error("This Notion database has no title property.");

  const database: SelectedNotionDatabase = {
    id: body.id,
    name: titleOf(body),
    titleProperty,
  };
  return { database, credentials: result.credentials };
}
