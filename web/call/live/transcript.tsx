"use client";

/**
 * The conversation as it happens, both sides of it.
 *
 * Input:  transcription text streams from LiveKit -- the worker publishes what it
 *         heard you say and what it said back
 * Output: a scrolling column of turns, his and yours
 *
 * Speakers are told apart by comparing each stream's participant identity to our
 * own. Anything that is not us is him: the room only ever has the two of us.
 */

import { useLocalParticipant, useTranscriptions } from "@livekit/components-react";
import { useEffect, useMemo, useRef } from "react";

import type { TranscriptTurn } from "../review/review-data";

export function Transcript({ onTurnsChange }: { onTurnsChange: (turns: TranscriptTurn[]) => void }) {
  const turns = useTranscriptions();
  const { localParticipant } = useLocalParticipant();
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
  }, [onTurnsChange, reviewTurns]);

  // Follow the conversation down, but only while the reader is already at the
  // bottom -- yanking the view away from someone scrolling back is worse than
  // making them scroll down again.
  useEffect(() => {
    const box = scroller.current;
    if (!box) return;
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
    if (atBottom) bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  return (
    <section className="column">
      <h2>Conversation</h2>
      <div className="scroller" ref={scroller}>
        {turns.length === 0 ? (
          <p className="empty">
            He is listening. Say something &mdash; a problem you actually have
            works better than a test question.
          </p>
        ) : (
          reviewTurns.map((turn) => {
            const mine = turn.speaker === "you";
            return (
              <p
                key={turn.id}
                className={`turn ${mine ? "you" : "him"}`}
              >
                <span className="who">{mine ? "You" : "Epictetus"}</span>
                <span className="what">{turn.text}</span>
              </p>
            );
          })
        )}
        <div ref={bottom} />
      </div>
    </section>
  );
}
