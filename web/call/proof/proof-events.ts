import type { TranscriptTurn } from "../review/review-data";

export type ProofAdmission = {
  roomName: string;
  lifetime: string;
  agentName: string;
  permissions: string[];
};

type ProofSource = {
  citation: string;
  title?: string;
  text?: string;
  score?: number;
};

export type ProofEvent = {
  kind: "event";
  id: string;
  category: "room" | "rag" | "tool";
  title: string;
  detail: string;
  sources?: ProofSource[];
};

export type ProofTurn = {
  kind: "turn";
  turn: TranscriptTurn;
};

export type ProofTimelineItem = ProofEvent | ProofTurn;

let eventSequence = 0;

function eventId(category: ProofEvent["category"]) {
  eventSequence += 1;
  return `${category}-${eventSequence}`;
}

export function admissionEvent(admission: ProofAdmission): ProofEvent {
  return {
    kind: "event",
    id: eventId("room"),
    category: "room",
    title: "Room admitted",
    detail: `${admission.roomName} · ${admission.lifetime} · ${admission.permissions.join(
      ", ",
    )} · dispatched ${admission.agentName}`,
  };
}

function readableScore(score: number | null, threshold: number, status: string) {
  if (score === null) return "No similarity score";
  const relation = status === "grounded" ? "≥" : "<";
  return `${score.toFixed(3)} ${relation} ${threshold.toFixed(3)}`;
}

export function ragEventFromMessage(body: unknown): ProofEvent | null {
  const message = body as {
    sources?: unknown;
    rag?: {
      status?: unknown;
      method?: unknown;
      bestCosine?: unknown;
      threshold?: unknown;
      reason?: unknown;
      selected?: unknown;
    };
  };
  const rag = message?.rag;
  if (
    !rag ||
    typeof rag.status !== "string" ||
    typeof rag.method !== "string" ||
    typeof rag.threshold !== "number" ||
    typeof rag.reason !== "string" ||
    typeof rag.selected !== "number"
  ) {
    return null;
  }
  const score = typeof rag.bestCosine === "number" ? rag.bestCosine : null;
  const sources = Array.isArray(message.sources)
    ? message.sources.filter(
        (source): source is ProofSource =>
          typeof source === "object" &&
          source !== null &&
          typeof (source as ProofSource).citation === "string",
      )
    : [];
  const title =
    rag.status === "grounded"
      ? "RAG grounded this turn"
      : rag.status === "rejected"
        ? "RAG rejected this turn"
        : rag.status === "skipped"
          ? "RAG skipped this turn"
          : "RAG could not run";
  const citations = sources.map((source) => source.citation).join("; ");
  const selection =
    rag.selected > 0
      ? `${rag.selected} passage${rag.selected === 1 ? "" : "s"} selected${
          citations ? `: ${citations}` : ""
        }`
      : "No passages added";

  return {
    kind: "event",
    id: eventId("rag"),
    category: "rag",
    title,
    detail: `${rag.method} · ${readableScore(score, rag.threshold, rag.status)} · ${selection} · ${rag.reason}`,
    sources,
  };
}

export function toolEventFromMessage(body: unknown): ProofEvent | null {
  const activity = body as { action?: unknown; detail?: unknown };
  if (typeof activity?.action !== "string") return null;
  const detail = typeof activity.detail === "string" ? activity.detail.trim() : "";
  return {
    kind: "event",
    id: eventId("tool"),
    category: "tool",
    title: "Tool call",
    detail: detail ? `${activity.action}: ${detail}` : activity.action,
  };
}

export function appendEvent(items: ProofTimelineItem[], event: ProofEvent) {
  return [...items, event];
}

export function addOrUpdateTurns(
  items: ProofTimelineItem[],
  turns: TranscriptTurn[],
): ProofTimelineItem[] {
  const next = [...items];
  for (const turn of turns) {
    const existing = next.findIndex(
      (item) => item.kind === "turn" && item.turn.id === turn.id,
    );
    if (existing >= 0) {
      next[existing] = { kind: "turn", turn };
    } else {
      next.push({ kind: "turn", turn });
    }
  }
  return next;
}
