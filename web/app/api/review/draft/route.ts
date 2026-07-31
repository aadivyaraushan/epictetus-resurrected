import { NextResponse } from "next/server";

import { draftReview } from "../../../../review/draft/openai-review";
import { DraftRateLimiter } from "../../../../review/draft/access/review-access";
import {
  clearReviewPermit,
  hasReviewPermit,
} from "../../../../review/draft/access/review-access-cookie";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_TRANSCRIPT_CHARS = 60_000;
const MAX_COMMITMENT_CHARS = 2_000;
const limiter = new DraftRateLimiter(3, 60 * 60_000);

export async function POST(request: Request) {
  if (!hasReviewPermit(request)) {
    return NextResponse.json({ error: "Finish a call before drafting its review." }, { status: 401 });
  }
  const address = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  if (!limiter.take(address)) {
    console.warn("[review.draft] rate limit reached");
    return NextResponse.json({ error: "Too many review drafts. Try again later." }, { status: 429 });
  }
  try {
    const body = (await request.json()) as {
      transcript?: unknown;
      capturedCommitment?: unknown;
    };
    if (typeof body.transcript !== "string" || !body.transcript.trim()) {
      return NextResponse.json({ error: "A transcript is required." }, { status: 400 });
    }
    if (body.transcript.length > MAX_TRANSCRIPT_CHARS) {
      return NextResponse.json({ error: "This transcript is too long to draft." }, { status: 413 });
    }
    const capturedCommitment =
      typeof body.capturedCommitment === "string" ? body.capturedCommitment : "";
    if (capturedCommitment.length > MAX_COMMITMENT_CHARS) {
      return NextResponse.json({ error: "The captured next step is too long." }, { status: 413 });
    }
    console.info(
      `[review.draft] received transcript_chars=${body.transcript.length} captured_commitment=${Boolean(capturedCommitment)}`,
    );
    const draft = await draftReview(
      { transcript: body.transcript, capturedCommitment },
      process.env.OPENAI_API_KEY ?? "",
    );
    console.info(
      `[review.draft] produced summary_chars=${draft.summary.length} next_step=${Boolean(draft.nextStep)}`,
    );
    const response = NextResponse.json(draft);
    clearReviewPermit(response);
    return response;
  } catch (error) {
    console.error("[review.draft] failed", error);
    return NextResponse.json({ error: "Could not draft this review." }, { status: 502 });
  }
}
