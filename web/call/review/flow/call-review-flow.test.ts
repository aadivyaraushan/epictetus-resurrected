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
    );

    expect(review.capturedCommitment).toBe(commitment);
    expect(formatTranscript(review.turns)).toBe(
      "You: I will do it tomorrow.\n\nEpictetus: Then name the hour.",
    );
  });

  it("ignores reflection and malformed activity messages", () => {
    expect(readCommitmentActivity({ kind: "reflection", commitment: "A fear." })).toBeNull();
    expect(readCommitmentActivity({ kind: "commitment", commitment: 42 })).toBeNull();
  });
});
