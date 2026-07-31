"use client";

/**
 * The call itself: transcript on the left, what he is reading on the right.
 *
 * Input:  the connected room (from LiveKitRoom, one level up)
 * Output: the whole live screen, plus the controls that end it
 *
 * The agent's own state -- listening, thinking, speaking -- comes from
 * useVoiceAssistant and drives one coloured dot. On a voice call the single most
 * useful thing a screen can tell you is whose turn it is.
 */

import {
  BarVisualizer,
  useLocalParticipant,
  useRoomContext,
  useVoiceAssistant,
} from "@livekit/components-react";
import { useCallback, useState } from "react";

import { SourcePanel } from "./panels/source-panel";
import { ToolActivity } from "./panels/tool-activity";
import { Transcript } from "./transcript";
import type { TranscriptTurn } from "../review/review-data";

// LiveKit reports more states than a caller needs to distinguish. Anything not
// named here is "connecting", which is what it looks like from the outside.
const SAID_PLAINLY: Record<string, { label: string; tone: string }> = {
  listening: { label: "Listening", tone: "listening" },
  thinking: { label: "Thinking", tone: "thinking" },
  speaking: { label: "Speaking", tone: "speaking" },
};

export function CallView({
  reviewDestination,
  onTurnsChange,
  onCommitment,
  onEndCall,
}: {
  reviewDestination: string | null;
  onTurnsChange: (turns: TranscriptTurn[]) => void;
  onCommitment: (text: string) => void;
  onEndCall: () => void;
}) {
  const { state, audioTrack } = useVoiceAssistant();
  const { localParticipant, isMicrophoneEnabled } = useLocalParticipant();
  const room = useRoomContext();
  const [leaving, setLeaving] = useState(false);

  const hangUp = useCallback(async () => {
    setLeaving(true);
    onEndCall();
    try {
      await room.disconnect();
    } catch (error) {
      console.error("[call-view] disconnect failed", error);
    }
  }, [room, onEndCall]);

  const toggleMic = useCallback(() => {
    localParticipant?.setMicrophoneEnabled(!isMicrophoneEnabled);
  }, [localParticipant, isMicrophoneEnabled]);

  const said = SAID_PLAINLY[state] ?? { label: "Connecting", tone: "" };

  return (
    <>
      <header className="masthead">
        <div className="brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="mark"
            src="/epictetus.png"
            alt=""
            width={396}
            height={560}
          />
          <div>
            <h1>Epictetus, Resurrected</h1>
            <p className="sub">Nicopolis, c. 108 &mdash; and now</p>
          </div>
        </div>
        <span className="badge">
          {reviewDestination ? `reviews → ${reviewDestination}` : "review after call"}
        </span>
      </header>

      <div className="call">
        <Transcript onTurnsChange={onTurnsChange} />
        <div className="column">
          <SourcePanel />
          <ToolActivity onCommitment={onCommitment} />
        </div>
      </div>

      <footer className="controls">
        <span className="status">
          <span className={`dot ${said.tone}`} aria-hidden="true" />
          {said.label}
          {audioTrack && (
            <BarVisualizer
              trackRef={audioTrack}
              barCount={5}
              style={{ width: 44, height: 18 }}
            />
          )}
        </span>

        <button
          type="button"
          className="quiet"
          aria-pressed={!isMicrophoneEnabled}
          onClick={toggleMic}
        >
          {isMicrophoneEnabled ? "Mute" : "Unmute"}
        </button>

        <button type="button" className="danger" onClick={hangUp} disabled={leaving}>
          {leaving ? "Ending…" : "End Call"}
        </button>
      </footer>
    </>
  );
}
