"use client";

/**
 * The app moves from setup, to a call, to an editable completed review.
 *
 * Input:  a Notion connection choice and a click on Start Call
 * Output: setup, a live call, or the completed review screen
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
import { useCallback, useEffect, useRef, useState } from "react";

import { CallView } from "../call/live/call-view";
import { ReviewScreen } from "../call/review/review-screen";
import type { CallReviewSource, TranscriptTurn } from "../call/review/review-data";
import { finishCallReview } from "../call/review/flow/call-review-flow";
import {
  StartScreen,
  type NotionConnection,
} from "../call/start-screen/start-screen";
import { callRecoveryMessage } from "../call/start-screen/recovery/call-recovery";

type Admission = {
  serverUrl: string;
  token: string;
};

const EMPTY_NOTION: NotionConnection = { connected: false };

export default function Page() {
  const [admission, setAdmission] = useState<Admission | null>(null);
  const [review, setReview] = useState<CallReviewSource | null>(null);
  const [notion, setNotion] = useState<NotionConnection>(EMPTY_NOTION);
  const [notionBusy, setNotionBusy] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [callFailure, setCallFailure] = useState<string | null>(null);
  const [notionFailure, setNotionFailure] = useState<string | null>(null);
  const source = useRef<CallReviewSource>({ turns: [], capturedCommitment: "" });

  const loadNotion = useCallback(async () => {
    setNotionBusy(true);
    try {
      const response = await fetch("/api/notion", { cache: "no-store" });
      const body = await response.json();
      if (!response.ok) throw new Error(body?.error ?? "Could not load Notion.");
      setNotion(body);
    } catch (error) {
      console.error("[page.notion] status failed", error);
      setNotionFailure("Could not load the Notion connection. Please try again.");
    } finally {
      setNotionBusy(false);
    }
  }, []);

  useEffect(() => {
    void loadNotion();
    const params = new URLSearchParams(window.location.search);
    const notionError = params.get("notion_error");
    if (notionError) {
      console.error("[page.notion] callback failed", notionError);
      setNotionFailure("Could not connect Notion. Try connecting again.");
    }
    if (params.has("notion")) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [loadNotion]);

  const startCall = useCallback(async () => {
    setConnecting(true);
    setCallFailure(null);
    source.current = { turns: [], capturedCommitment: "" };
    try {
      const response = await fetch("/api/token", { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(body?.error ?? `Token request failed (${response.status}).`);
      setAdmission({ serverUrl: body.serverUrl, token: body.token });
    } catch (error) {
      console.error("[page] could not start the call", error);
      setCallFailure(callRecoveryMessage("admission", error));
      setConnecting(false);
    }
  }, []);

  const leaveCall = useCallback(() => {
    setAdmission(null);
    setConnecting(false);
  }, []);

  const completeCall = useCallback(() => {
    setReview(
      finishCallReview(source.current.turns, source.current.capturedCommitment),
    );
    leaveCall();
  }, [leaveCall]);

  const rememberTurns = useCallback((turns: TranscriptTurn[]) => {
    source.current.turns = turns;
  }, []);

  const rememberCommitment = useCallback((text: string) => {
    source.current.capturedCommitment = text;
  }, []);

  const disconnectNotion = useCallback(async () => {
    setNotionBusy(true);
    setNotionFailure(null);
    try {
      await fetch("/api/notion", { method: "DELETE" });
      setNotion(EMPTY_NOTION);
    } catch (error) {
      console.error("[page.notion] disconnect failed", error);
      setNotionFailure("Could not disconnect Notion. Please try again.");
    } finally {
      setNotionBusy(false);
    }
  }, []);

  if (review) {
    return (
      <ReviewScreen
        source={review}
        databaseName={notion.connected ? notion.selectedDatabase.name : null}
        onNewCall={() => {
          setReview(null);
          setCallFailure(null);
          setNotionFailure(null);
          void loadNotion();
        }}
      />
    );
  }

  if (!admission) {
    return (
      <StartScreen
        onStart={startCall}
        connecting={connecting}
        callFailure={callFailure}
        notionFailure={notionFailure}
        notion={notion}
        notionBusy={notionBusy}
        onDisconnectNotion={disconnectNotion}
      />
    );
  }

  return (
    <LiveKitRoom
      serverUrl={admission.serverUrl}
      token={admission.token}
      connect={true}
      audio={true} // publish the microphone as soon as we are in
      video={false}
      onDisconnected={leaveCall}
      onError={(error) => {
        console.error("[page] room error", error);
        setCallFailure(callRecoveryMessage("room", error));
        leaveCall();
      }}
      className="shell live-shell"
    >
      {/* Without this nothing he says is audible -- it renders the audio elements. */}
      <RoomAudioRenderer />
      <CallView
        reviewDestination={notion.connected ? notion.selectedDatabase.name : null}
        onTurnsChange={rememberTurns}
        onCommitment={rememberCommitment}
        onEndCall={completeCall}
      />
    </LiveKitRoom>
  );
}
