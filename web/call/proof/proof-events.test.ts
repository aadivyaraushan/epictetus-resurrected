import { describe, expect, it } from "vitest";

import type { TranscriptTurn } from "../review/review-data";
import {
  addOrUpdateTurns,
  admissionEvent,
  appendEvent,
  ragEventFromMessage,
  toolEventFromMessage,
  type ProofTimelineItem,
} from "./proof-events";

describe("proof-call events", () => {
  it("turns safe admission facts into the first timeline annotation", () => {
    const event = admissionEvent({
      roomName: "epictetus-room-1",
      lifetime: "30 minutes",
      agentName: "epictetus",
      permissions: ["join this room", "publish microphone and data", "subscribe"],
    });

    expect(event).toMatchObject({
      kind: "event",
      category: "room",
      title: "Room admitted",
    });
    expect(event.detail).toContain("epictetus-room-1");
    expect(event.detail).toContain("30 minutes");
    expect(event.detail).not.toContain("token");
  });

  it("reads grounded and rejected RAG decisions from the existing source topic", () => {
    const grounded = ragEventFromMessage({
      sources: [{ citation: "Book 1, Chapter 1" }],
      rag: {
        status: "grounded",
        method: "vector + BM25, merged by reciprocal rank fusion",
        bestCosine: 0.51,
        threshold: 0.36,
        reason: "above gate",
        selected: 1,
      },
    });
    const rejected = ragEventFromMessage({
      sources: [],
      rag: {
        status: "rejected",
        method: "vector + BM25, merged by reciprocal rank fusion",
        bestCosine: 0.31,
        threshold: 0.36,
        reason: "below gate",
        selected: 0,
      },
    });

    expect(grounded).toMatchObject({ category: "rag", title: "RAG grounded this turn" });
    expect(grounded?.detail).toContain("0.510 ≥ 0.360");
    expect(grounded?.detail).toContain("Book 1, Chapter 1");
    expect(rejected).toMatchObject({ category: "rag", title: "RAG rejected this turn" });
    expect(rejected?.detail).toContain("0.310 < 0.360");
    expect(rejected?.detail).toContain("below gate");
  });

  it("makes skipped and failed retrieval visible instead of silently omitting them", () => {
    const skipped = ragEventFromMessage({
      sources: [],
      rag: {
        status: "skipped",
        method: "word-count check before retrieval",
        bestCosine: null,
        threshold: 0.36,
        reason: "fewer than 4 words",
        selected: 0,
      },
    });
    const failed = ragEventFromMessage({
      sources: [],
      rag: {
        status: "error",
        method: "vector + BM25, merged by reciprocal rank fusion",
        bestCosine: null,
        threshold: 0.36,
        reason: "retrieval failed; answered without passages",
        selected: 0,
      },
    });

    expect(skipped).toMatchObject({ category: "rag", title: "RAG skipped this turn" });
    expect(skipped?.detail).toContain("No similarity score");
    expect(skipped?.detail).toContain("fewer than 4 words");
    expect(failed).toMatchObject({ category: "rag", title: "RAG could not run" });
    expect(failed?.detail).toContain("retrieval failed; answered without passages");
  });

  it("reads tool activity without treating malformed data as proof", () => {
    expect(
      toolEventFromMessage({ action: "looking up", detail: "cold plunging" }),
    ).toMatchObject({
      category: "tool",
      title: "Tool call",
      detail: "looking up: cold plunging",
    });
    expect(toolEventFromMessage({ detail: "missing action" })).toBeNull();
  });

  it("keeps annotations between their turns while streaming text updates", () => {
    const admission = admissionEvent({
      roomName: "room-1",
      lifetime: "30 minutes",
      agentName: "epictetus",
      permissions: ["join this room"],
    });
    const firstUser: TranscriptTurn = { id: "u1", speaker: "you", text: "Why did" };
    const finalUser: TranscriptTurn = {
      id: "u1",
      speaker: "you",
      text: "Why did you compare bad company to burning charcoal?",
    };
    const answer: TranscriptTurn = { id: "a1", speaker: "epictetus", text: "Consider this." };
    const rag = ragEventFromMessage({
      sources: [{ citation: "Book 3, Chapter 16" }],
      rag: {
        status: "grounded",
        method: "vector + BM25, merged by reciprocal rank fusion",
        bestCosine: 0.49,
        threshold: 0.36,
        reason: "above gate",
        selected: 1,
      },
    });

    let items: ProofTimelineItem[] = [admission];
    items = addOrUpdateTurns(items, [firstUser]);
    items = appendEvent(items, rag!);
    items = addOrUpdateTurns(items, [finalUser, answer]);

    expect(items.map((item) => item.kind === "turn" ? item.turn.id : item.category)).toEqual([
      "room",
      "u1",
      "rag",
      "a1",
    ]);
    expect(items[1]).toMatchObject({ kind: "turn", turn: finalUser });
  });
});
