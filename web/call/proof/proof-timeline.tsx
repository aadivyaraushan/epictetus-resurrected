"use client";

import {
  useDataChannel,
  useLocalParticipant,
  useTranscriptions,
} from "@livekit/components-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { readCommitmentActivity } from "../review/flow/call-review-flow";
import type { TranscriptTurn } from "../review/review-data";
import {
  addOrUpdateTurns,
  admissionEvent,
  appendEvent,
  ragEventFromMessage,
  toolEventFromMessage,
  type ProofAdmission,
  type ProofTimelineItem,
} from "./proof-events";

const SOURCE_TOPIC = "epictetus.sources";
const ACTIVITY_TOPIC = "epictetus.activity";

export function ProofTimeline({
  admission,
  onTurnsChange,
  onCommitment,
}: {
  admission: ProofAdmission;
  onTurnsChange: (turns: TranscriptTurn[]) => void;
  onCommitment: (text: string) => void;
}) {
  const turns = useTranscriptions();
  const { localParticipant } = useLocalParticipant();
  const [items, setItems] = useState<ProofTimelineItem[]>(() => [admissionEvent(admission)]);
  const scroller = useRef<HTMLDivElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const reviewTurns = useMemo(
    () =>
      turns.map((turn) => ({
        id: turn.streamInfo.id,
        speaker:
          turn.participantInfo.identity === localParticipant?.identity
            ? ("you" as const)
            : ("epictetus" as const),
        text: turn.text,
      })),
    [turns, localParticipant?.identity],
  );

  useEffect(() => {
    onTurnsChange(reviewTurns);
    setItems((previous) => addOrUpdateTurns(previous, reviewTurns));
  }, [onTurnsChange, reviewTurns]);

  const receiveRag = useCallback((message: { payload: Uint8Array }) => {
    try {
      const event = ragEventFromMessage(JSON.parse(new TextDecoder().decode(message.payload)));
      if (event) setItems((previous) => appendEvent(previous, event));
    } catch (error) {
      console.error("[proof-timeline] could not read a RAG event", error);
    }
  }, []);

  const receiveTool = useCallback(
    (message: { payload: Uint8Array }) => {
      try {
        const body = JSON.parse(new TextDecoder().decode(message.payload));
        const commitment = readCommitmentActivity(body);
        if (commitment) onCommitment(commitment);
        const event = toolEventFromMessage(body);
        if (event) setItems((previous) => appendEvent(previous, event));
      } catch (error) {
        console.error("[proof-timeline] could not read a tool event", error);
      }
    },
    [onCommitment],
  );

  useDataChannel(SOURCE_TOPIC, receiveRag);
  useDataChannel(ACTIVITY_TOPIC, receiveTool);

  useEffect(() => {
    const box = scroller.current;
    if (!box) return;
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 140;
    if (atBottom) bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [items]);

  return (
    <section className="column proof-timeline">
      <h2>Proof timeline</h2>
      <div className="scroller" ref={scroller}>
        {/* The first annotation is always "Room admitted"; no signed token is stored here. */}
        {items.map((item) => {
          if (item.kind === "turn") {
            const mine = item.turn.speaker === "you";
            return (
              <p className={`turn ${mine ? "you" : "him"}`} key={`turn-${item.turn.id}`}>
                <span className="who">{mine ? "You" : "Epictetus"}</span>
                <span className="what">{item.turn.text}</span>
              </p>
            );
          }
          return (
            <article className={`proof-event ${item.category}`} key={item.id}>
              <div className="proof-event-label">{item.title}</div>
              <p>{item.detail}</p>
              {item.sources?.map((source, index) => (
                <details className="proof-source" key={`${item.id}-${source.citation}-${index}`}>
                  <summary>{source.citation}</summary>
                  {source.title && <div className="title">{source.title}</div>}
                  {source.text && <p>{source.text}</p>}
                </details>
              ))}
            </article>
          );
        })}
        <div ref={bottom} />
      </div>
    </section>
  );
}
