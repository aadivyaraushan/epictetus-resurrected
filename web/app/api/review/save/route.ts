import { NextResponse } from "next/server";

import { requestNotion } from "../../../../notion/connection/client/notion-client";
import {
  notionSessionFrom,
  storeNotionSession,
} from "../../../../notion/connection/cookie/session-cookie";
import {
  buildReviewPage,
  type CompletedReview,
} from "../../../../review/storage/notion-review";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function oauthClient() {
  const clientId = process.env.NOTION_OAUTH_CLIENT_ID;
  const clientSecret = process.env.NOTION_OAUTH_CLIENT_SECRET;
  return clientId && clientSecret ? { clientId, clientSecret } : undefined;
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as Partial<CompletedReview> & { completed?: unknown };
    if (body.completed !== true) {
      return NextResponse.json({ error: "Only completed reviews can be saved." }, { status: 400 });
    }
    const session = notionSessionFrom(request);
    if (!session?.selectedDatabase) {
      return NextResponse.json(
        { error: "Reconnect Notion and share exactly one database before saving." },
        { status: 409 },
      );
    }
    const fields = [body.title, body.summary, body.nextStep, body.transcript];
    if (fields.some((field) => typeof field !== "string")) {
      return NextResponse.json({ error: "The completed review is missing fields." }, { status: 400 });
    }
    const review = body as CompletedReview;
    console.info(
      `[review.save] received database=${session.selectedDatabase.id} transcript_chars=${review.transcript.length}`,
    );
    const result = await requestNotion(
      { accessToken: session.accessToken, refreshToken: session.refreshToken },
      "/v1/pages",
      { method: "POST", body: JSON.stringify(buildReviewPage(review, session.selectedDatabase)) },
      fetch,
      oauthClient(),
    );
    if (!result.response.ok) throw new Error(`Notion page creation returned ${result.response.status}`);
    const page = (await result.response.json()) as { id?: string };
    if (!page.id) throw new Error("Notion page creation returned no page id");

    const response = NextResponse.json({ saved: true, pageId: page.id });
    if (
      result.credentials.accessToken !== session.accessToken ||
      result.credentials.refreshToken !== session.refreshToken
    ) {
      storeNotionSession(response, { ...session, ...result.credentials });
    }
    console.info(`[review.save] created page ${page.id}`);
    return response;
  } catch (error) {
    console.error("[review.save] failed", error);
    return NextResponse.json({ error: "Could not save this review to Notion." }, { status: 502 });
  }
}
