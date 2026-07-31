import type { SelectedNotionDatabase } from "../../notion/connection/session/session";
import type { ReferencedChapter } from "../../call/review/review-data";

export type CompletedReview = {
  title: string;
  summary: string;
  nextStep: string;
  transcript: string;
  chaptersReferenced: ReferencedChapter[];
};

type RichText = { type: "text"; text: { content: string } };
type Block = {
  object: "block";
  type: "heading_2" | "paragraph";
  heading_2?: { rich_text: RichText[] };
  paragraph?: { rich_text: RichText[] };
};

const MAX_RICH_TEXT = 1900;

export function splitRichText(text: string) {
  const chunks: string[] = [];
  for (let start = 0; start < text.length; start += MAX_RICH_TEXT) {
    chunks.push(text.slice(start, start + MAX_RICH_TEXT));
  }
  return chunks.length ? chunks : [""];
}

function richText(content: string): RichText[] {
  return content ? [{ type: "text", text: { content } }] : [];
}

function heading(content: string): Block {
  return { object: "block", type: "heading_2", heading_2: { rich_text: richText(content) } };
}

function paragraphs(content: string): Block[] {
  return splitRichText(content).map((chunk) => ({
    object: "block",
    type: "paragraph",
    paragraph: { rich_text: richText(chunk) },
  }));
}

export function buildReviewPage(
  review: CompletedReview,
  database: SelectedNotionDatabase,
) {
  const chaptersReferenced = review.chaptersReferenced ?? [];
  const chapterList = chaptersReferenced.length
    ? chaptersReferenced.map((chapter) => `${chapter.citation} — ${chapter.title}`).join("\n")
    : "None recorded during this call.";
  return {
    parent: { data_source_id: database.id },
    properties: {
      [database.titleProperty]: {
        title: richText(review.title),
      },
    },
    children: [
      heading("Summary"),
      ...paragraphs(review.summary),
      heading("Next step"),
      ...paragraphs(review.nextStep),
      heading("Chapters referenced"),
      ...paragraphs(chapterList),
      heading("Transcript"),
      ...paragraphs(review.transcript),
    ],
  };
}
