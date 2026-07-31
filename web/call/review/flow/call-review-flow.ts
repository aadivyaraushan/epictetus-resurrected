import type { CallReviewSource, TranscriptTurn } from "../review-data";

export function readCommitmentActivity(body: unknown) {
  const activity = body as { kind?: unknown; commitment?: unknown };
  if (activity?.kind !== "commitment" || typeof activity.commitment !== "string") {
    return null;
  }
  const commitment = activity.commitment.trim();
  return commitment || null;
}

export function finishCallReview(
  turns: TranscriptTurn[],
  capturedCommitment: string,
): CallReviewSource {
  return { turns: [...turns], capturedCommitment };
}
