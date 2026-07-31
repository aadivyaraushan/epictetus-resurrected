import { describe, expect, it } from "vitest";

import { formatTranscript, reviewTitle } from "./review-data";

describe("review data captured from a complete call", () => {
  it("keeps both speakers in order and drops empty partial turns", () => {
    expect(
      formatTranscript([
        { id: "1", speaker: "you", text: "I am avoiding the reply." },
        { id: "2", speaker: "epictetus", text: "What part is yours?" },
        { id: "3", speaker: "you", text: "   " },
      ]),
    ).toBe("You: I am avoiding the reply.\n\nEpictetus: What part is yours?");
  });

  it("uses the caller's local date in the page title", () => {
    expect(reviewTitle(new Date("2026-07-31T18:00:00Z"), "en-US", "UTC")).toBe(
      "Evening Review — July 31, 2026",
    );
  });
});
