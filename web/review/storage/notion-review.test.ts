import { describe, expect, it } from "vitest";

import { buildReviewPage, splitRichText } from "./notion-review";

describe("completed Notion review", () => {
  it("creates one page with the detected title property and all review sections", () => {
    const page = buildReviewPage(
      {
        title: "Evening Review — July 31, 2026",
        summary: "The user focused on what they can control.",
        nextStep: "Send the outline tomorrow morning.",
        transcript: "You: I will send it.\nEpictetus: At what time?",
        chaptersReferenced: [
          { citation: "Book 2, Chapter 1", title: "On Tranquillity" },
          { citation: "Book 4, Chapter 1", title: "About Freedom" },
        ],
      },
      { id: "review-source", name: "Evening Reviews", titleProperty: "Reflection" },
    );

    expect(page.parent).toEqual({ data_source_id: "review-source" });
    expect(page.properties).toEqual({
      Reflection: {
        title: [{ type: "text", text: { content: "Evening Review — July 31, 2026" } }],
      },
    });
    expect(JSON.stringify(page.children)).toContain("Summary");
    expect(JSON.stringify(page.children)).toContain("Next step");
    expect(JSON.stringify(page.children)).toContain("Transcript");
    expect(JSON.stringify(page.children)).toContain("Chapters referenced");
    expect(JSON.stringify(page.children)).toContain("Book 4, Chapter 1 — About Freedom");
    expect(JSON.stringify(page.children)).toContain("Send the outline tomorrow morning.");
  });

  it("splits long transcript text without losing a character", () => {
    const transcript = `${"one ".repeat(650)}done`;
    const chunks = splitRichText(transcript);

    expect(chunks.every((chunk) => chunk.length <= 1900)).toBe(true);
    expect(chunks.join("")).toBe(transcript);
  });
});
