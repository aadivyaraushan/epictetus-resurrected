export type TranscriptTurn = {
  id: string;
  speaker: "you" | "epictetus";
  text: string;
};

export type ReferencedChapter = {
  citation: string;
  title: string;
};

export type CallReviewSource = {
  turns: TranscriptTurn[];
  capturedCommitment: string;
  chaptersReferenced: ReferencedChapter[];
};

export function mergeReferencedChapters(
  previous: ReferencedChapter[],
  incoming: ReferencedChapter[],
) {
  const merged = [...previous];
  const seen = new Set(previous.map((chapter) => chapter.citation));
  for (const chapter of incoming) {
    const citation = typeof chapter.citation === "string" ? chapter.citation.trim() : "";
    if (!citation || seen.has(citation)) continue;
    seen.add(citation);
    const title = typeof chapter.title === "string" ? chapter.title.trim() : "";
    merged.push({ citation, title });
  }
  return merged;
}

export function formatTranscript(turns: TranscriptTurn[]) {
  return turns
    .filter((turn) => turn.text.trim())
    .map((turn) => `${turn.speaker === "you" ? "You" : "Epictetus"}: ${turn.text.trim()}`)
    .join("\n\n");
}

export function reviewTitle(
  date = new Date(),
  locale?: string,
  timeZone?: string,
) {
  const formatted = new Intl.DateTimeFormat(locale, {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone,
  }).format(date);
  return `Evening Review — ${formatted}`;
}
