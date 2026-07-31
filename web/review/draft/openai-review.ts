export type ReviewDraftInput = {
  transcript: string;
  capturedCommitment: string;
};

export type ReviewDraft = {
  summary: string;
  nextStep: string;
};

type ParsedReview = {
  summary: string;
  explicitNextStep: string;
};

type ResponseContent = { type?: string; text?: string; refusal?: string };
type ResponseItem = { type?: string; content?: ResponseContent[] };

export function parseReviewResponse(body: unknown): ParsedReview {
  const response = body as { status?: string; output?: ResponseItem[] };
  if (response.status !== "completed") {
    throw new Error("OpenAI did not complete the review draft.");
  }
  const content = response.output
    ?.find((item) => item.type === "message")
    ?.content?.find((part) => part.type === "output_text");
  if (!content?.text) throw new Error("OpenAI returned no review draft.");

  const parsed = JSON.parse(content.text) as Partial<ParsedReview>;
  if (typeof parsed.summary !== "string" || typeof parsed.explicitNextStep !== "string") {
    throw new Error("OpenAI returned an invalid review draft.");
  }
  return { summary: parsed.summary.trim(), explicitNextStep: parsed.explicitNextStep.trim() };
}

export async function draftReview(
  input: ReviewDraftInput,
  apiKey: string,
  fetcher: typeof fetch = fetch,
): Promise<ReviewDraft> {
  if (!apiKey) throw new Error("OPENAI_API_KEY is missing.");

  const response = await fetcher("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "gpt-5.6-luna",
      store: false,
      max_output_tokens: 500,
      reasoning: { effort: "minimal" },
      input: [
        {
          role: "system",
          content:
            "Draft a concise evening-review summary from the call transcript. Report what the user reflected on and the useful conclusion they reached. For explicitNextStep, copy only a clear action the user personally committed to doing; return an empty string if none appears. Do not invent commitments.",
        },
        {
          role: "user",
          content: `Transcript:\n${input.transcript}`,
        },
      ],
      text: {
        format: {
          type: "json_schema",
          name: "evening_review",
          strict: true,
          schema: {
            type: "object",
            properties: {
              summary: { type: "string" },
              explicitNextStep: { type: "string" },
            },
            required: ["summary", "explicitNextStep"],
            additionalProperties: false,
          },
        },
      },
    }),
  });
  if (!response.ok) throw new Error(`OpenAI review draft failed (${response.status}).`);

  const parsed = parseReviewResponse(await response.json());
  return {
    summary: parsed.summary,
    nextStep: input.capturedCommitment.trim() || parsed.explicitNextStep,
  };
}
