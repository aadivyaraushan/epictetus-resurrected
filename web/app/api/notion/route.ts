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
  if (!session) return NextResponse.json({ connected: false });

  try {
    const result = await listSharedDatabases(
      { accessToken: session.accessToken, refreshToken: session.refreshToken },
      fetch,
      oauthClient(),
    );
    const databaseCount = result.databases.length;
    console.info(`[notion.database] found ${databaseCount} accessible databases`);

    if (databaseCount !== 1) {
      const reconnectMessage =
        databaseCount === 0
          ? "No database was shared. Reconnect and choose the Evening Reviews database itself."
          : "More than one database was shared. Reconnect and choose only the Evening Reviews database.";
      const response = NextResponse.json({ connected: false, reconnectMessage });
      clearNotionSession(response);
      console.warn(`[notion.database] rejected connection with ${databaseCount} databases`);
      return response;
    }

    const onlyDatabase = result.databases[0];
    let credentials = result.credentials;
    let selectedDatabase = session.selectedDatabase;
    if (selectedDatabase?.id === onlyDatabase.id) {
      selectedDatabase = { ...selectedDatabase, name: onlyDatabase.name };
    } else {
      const selection = await selectSharedDatabase(
        onlyDatabase.id,
        credentials,
        fetch,
        oauthClient(),
      );
      credentials = selection.credentials;
      selectedDatabase = selection.database;
    }

    const nextSession = { ...session, ...credentials, selectedDatabase };
    const response = NextResponse.json({
      connected: true,
      workspaceName: session.workspaceName,
      selectedDatabase,
    });
    storeNotionSession(response, nextSession);
    console.info(`[notion.database] bound database ${selectedDatabase.id}`);
    return response;
  } catch (error) {
    console.error("[notion.database] listing failed", error);
    return NextResponse.json({ error: "Could not load Notion databases." }, { status: 502 });
  }
}

export async function DELETE() {
  const response = NextResponse.json({ connected: false });
  clearNotionSession(response);
  console.info("[notion.oauth] workspace disconnected");
  return response;
}
