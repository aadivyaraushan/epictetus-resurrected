export type TranscriptTurn = {
  id: string;
  speaker: "you" | "epictetus";
  text: string;
};

export type CallReviewSource = {
  turns: TranscriptTurn[];
  capturedCommitment: string;
};

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
