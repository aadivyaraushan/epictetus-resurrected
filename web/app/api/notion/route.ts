import { NextResponse } from "next/server";

import {
  listSharedDatabases,
  selectSharedDatabase,
} from "../../../notion/connection/client/notion-client";
import {
  clearNotionSession,
  notionSessionFrom,
  storeNotionSession,
} from "../../../notion/connection/cookie/session-cookie";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function oauthClient() {
  const clientId = process.env.NOTION_OAUTH_CLIENT_ID;
  const clientSecret = process.env.NOTION_OAUTH_CLIENT_SECRET;
  return clientId && clientSecret ? { clientId, clientSecret } : undefined;
}

export async function GET(request: Request) {
  const session = notionSessionFrom(request);
  if (!session) return NextResponse.json({ connected: false, databases: [] });

  try {
    const result = await listSharedDatabases(
      { accessToken: session.accessToken, refreshToken: session.refreshToken },
      fetch,
      oauthClient(),
    );
    const response = NextResponse.json({
      connected: true,
      workspaceName: session.workspaceName,
      selectedDatabase: session.selectedDatabase ?? null,
      databases: result.databases,
    });
    if (
      result.credentials.accessToken !== session.accessToken ||
      result.credentials.refreshToken !== session.refreshToken
    ) {
      storeNotionSession(response, { ...session, ...result.credentials });
    }
    console.info(`[notion.database] listed ${result.databases.length} accessible databases`);
    return response;
  } catch (error) {
    console.error("[notion.database] listing failed", error);
    return NextResponse.json({ error: "Could not load Notion databases." }, { status: 502 });
  }
}

export async function POST(request: Request) {
  const session = notionSessionFrom(request);
  if (!session) return NextResponse.json({ error: "Connect Notion first." }, { status: 401 });

  try {
    const body = (await request.json()) as { dataSourceId?: unknown };
    if (typeof body.dataSourceId !== "string" || !body.dataSourceId.trim()) {
      return NextResponse.json({ error: "Choose a Notion database." }, { status: 400 });
    }
    const result = await selectSharedDatabase(
      body.dataSourceId,
      { accessToken: session.accessToken, refreshToken: session.refreshToken },
      fetch,
      oauthClient(),
    );
    const nextSession = {
      ...session,
      ...result.credentials,
      selectedDatabase: result.database,
    };
    const response = NextResponse.json({ selectedDatabase: result.database });
    storeNotionSession(response, nextSession);
    console.info(`[notion.database] selected database ${result.database.id}`);
    return response;
  } catch (error) {
    console.error("[notion.database] selection failed", error);
    return NextResponse.json({ error: "Could not select that Notion database." }, { status: 502 });
  }
}

export async function DELETE() {
  const response = NextResponse.json({ connected: false });
  clearNotionSession(response);
  console.info("[notion.oauth] workspace disconnected");
  return response;
}
