"use client";

/**
 * The whole app is one screen with two states: before the call and during it.
 *
 * Input:  a click on Start Call, and optionally a passphrase
 * Output: either the start screen or a live call
 *
 * Steps:
 *   1. Ask /api/token for a room and a token.
 *   2. Hand both to LiveKitRoom, which connects and publishes the microphone.
 *   3. Show the call until either End Call or a dropped connection.
 *
 * Kept in one component because there are only two states and a single piece of
 * data passed between them. A router or a state library would be more machinery
 * than the problem has.
 */

import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import { useCallback, useState } from "react";

import { CallView } from "../call/live/call-view";
import { StartScreen } from "../call/start-screen/start-screen";

type Admission = {
  serverUrl: string;
  token: string;
  backend: "live" | "demo";
};

export default function Page() {
  const [admission, setAdmission] = useState<Admission | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const startCall = useCallback(async (passphrase: string) => {
    setConnecting(true);
    setFailure(null);
    try {
      const response = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passphrase }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body?.error ?? `Token request failed (${response.status}).`);
      setAdmission({ serverUrl: body.serverUrl, token: body.token, backend: body.backend });
    } catch (error) {
      console.error("[page] could not start the call", error);
      setFailure(
        error instanceof Error
          ? error.message
          : "Could not reach the server that lets you into the room.",
      );
      setConnecting(false);
    }
  }, []);

  const endCall = useCallback(() => {
    setAdmission(null);
    setConnecting(false);
  }, []);

  if (!admission) {
    return (
      <StartScreen onStart={startCall} connecting={connecting} failure={failure} />
    );
  }

  return (
    <LiveKitRoom
      serverUrl={admission.serverUrl}
      token={admission.token}
      connect={true}
      audio={true} // publish the microphone as soon as we are in
      video={false}
      onDisconnected={endCall}
      onError={(error) => {
        console.error("[page] room error", error);
        setFailure(error.message);
        endCall();
      }}
      className="shell"
    >
      {/* Without this nothing he says is audible -- it renders the audio elements. */}
      <RoomAudioRenderer />
      <CallView backend={admission.backend} onEndCall={endCall} />
    </LiveKitRoom>
  );
}
