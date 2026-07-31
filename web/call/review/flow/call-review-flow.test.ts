import { describe, expect, it } from "vitest";

import { finishCallReview, readCommitmentActivity } from "./call-review-flow";
import { formatTranscript } from "../review-data";

describe("live call to completed review flow", () => {
  it("keeps a full long commitment even when the activity label is shortened", () => {
    const commitment = "Send the revised outline tomorrow morning, then message Dana with the three decisions and ask her to confirm the Friday review time.";
    const captured = readCommitmentActivity({
      action: "writing in the session log",
      detail: commitment.slice(0, 120),
      kind: "commitment",
      commitment,
    });
    const review = finishCallReview(
      [
        { id: "one", speaker: "you", text: "I will do it tomorrow." },
        { id: "two", speaker: "epictetus", text: "Then name the hour." },
      ],
      captured ?? "",
      [{ citation: "Book 2, Chapter 1", title: "On Tranquillity" }],
    );

    expect(review.capturedCommitment).toBe(commitment);
    expect(review.chaptersReferenced).toEqual([
      { citation: "Book 2, Chapter 1", title: "On Tranquillity" },
    ]);
    expect(formatTranscript(review.turns)).toBe(
      "You: I will do it tomorrow.\n\nEpictetus: Then name the hour.",
    );
  });

  it("ignores reflection and malformed activity messages", () => {
    expect(readCommitmentActivity({ kind: "reflection", commitment: "A fear." })).toBeNull();
    expect(readCommitmentActivity({ kind: "commitment", commitment: 42 })).toBeNull();
  });

  it("keeps only the first copy of each referenced chapter", async () => {
    const { mergeReferencedChapters } = await import("../review-data");

    expect(
      mergeReferencedChapters(
        [{ citation: "Book 2, Chapter 1", title: "On Tranquillity" }],
        [
          { citation: "Book 2, Chapter 1", title: "On Tranquillity" },
          { citation: "Book 4, Chapter 1", title: "About Freedom" },
        ],
      ),
    ).toEqual([
      { citation: "Book 2, Chapter 1", title: "On Tranquillity" },
      { citation: "Book 4, Chapter 1", title: "About Freedom" },
    ]);
  });
});
