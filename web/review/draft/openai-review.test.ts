import { describe, expect, it, vi } from "vitest";

import { draftReview, parseReviewResponse } from "./openai-review";

describe("review drafting", () => {
  it("asks Luna for only a summary and an explicit committed next step", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "completed",
          output: [
            {
              type: "message",
              content: [
                {
                  type: "output_text",
                  text: JSON.stringify({
                    summary: "The user separated the setback from what remains under their control.",
                    explicitNextStep: "Send the revised outline tomorrow morning.",
                  }),
                },
              ],
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const result = await draftReview(
      {
        transcript: "You: I lost the client.\nEpictetus: What remains yours?",
        capturedCommitment: "Email the revised outline tomorrow.",
      },
      "test-openai-key",
      fetcher,
    );

    expect(result).toEqual({
      summary: "The user separated the setback from what remains under their control.",
      nextStep: "Email the revised outline tomorrow.",
    });

    const request = JSON.parse(String(fetcher.mock.calls[0][1]?.body));
    expect(request.model).toBe("gpt-5.6-luna");
    expect(request.store).toBe(false);
    expect(request.max_output_tokens).toBe(500);
    expect(request.text.format).toMatchObject({
      type: "json_schema",
      name: "evening_review",
      strict: true,
    });
  });

  it("uses a transcript commitment only when no in-call commitment was captured", async () => {
    const parsed = parseReviewResponse({
      status: "completed",
      output: [
        {
          type: "message",
          content: [
            {
              type: "output_text",
              text: JSON.stringify({
                summary: "A concise summary.",
                explicitNextStep: "Book the appointment.",
              }),
            },
          ],
        },
      ],
    });

    expect(parsed).toEqual({
      summary: "A concise summary.",
      explicitNextStep: "Book the appointment.",
    });
  });

  it("fails clearly when OpenAI does not return a completed structured result", () => {
    expect(() => parseReviewResponse({ status: "incomplete", output: [] })).toThrow(
      "OpenAI did not complete the review draft",
    );
  });
});
