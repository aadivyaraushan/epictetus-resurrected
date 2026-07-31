"use client";

import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { CallView } from "../live/call-view";
import type { ProofAdmission } from "../proof/proof-events";
import { ReviewScreen } from "../review/review-screen";
import type {
  CallReviewSource,
  ReferencedChapter,
  TranscriptTurn,
} from "../review/review-data";
import { finishCallReview } from "../review/flow/call-review-flow";
import {
  StartScreen,
  type NotionConnection,
} from "../start-screen/start-screen";
import { callRecoveryMessage } from "../start-screen/recovery/call-recovery";

type Admission = {
  serverUrl: string;
  token: string;
  proof: ProofAdmission;
};

const EMPTY_NOTION: NotionConnection = { connected: false };

export function CallExperience({ proofMode = false }: { proofMode?: boolean }) {
  const [admission, setAdmission] = useState<Admission | null>(null);
  const [review, setReview] = useState<CallReviewSource | null>(null);
  const [notion, setNotion] = useState<NotionConnection>(EMPTY_NOTION);
  const [notionBusy, setNotionBusy] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [callFailure, setCallFailure] = useState<string | null>(null);
  const [notionFailure, setNotionFailure] = useState<string | null>(null);
  const source = useRef<CallReviewSource>({
    turns: [],
    capturedCommitment: "",
    chaptersReferenced: [],
  });

  const loadNotion = useCallback(async () => {
    setNotionBusy(true);
    try {
      const response = await fetch("/api/notion", { cache: "no-store" });
      const body = await response.json();
      if (!response.ok) throw new Error(body?.error ?? "Could not load Notion.");
      setNotion(body);
    } catch (error) {
      console.error("[call-experience] Notion status failed", error);
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
      console.error("[call-experience] Notion callback failed", notionError);
      setNotionFailure("Could not connect Notion. Try connecting again.");
    }
    if (params.has("notion")) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [loadNotion]);

  const startCall = useCallback(async () => {
    setConnecting(true);
    setCallFailure(null);
    source.current = { turns: [], capturedCommitment: "", chaptersReferenced: [] };
    try {
      const response = await fetch("/api/token", { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(body?.error ?? `Token request failed (${response.status}).`);
      if (!body?.proof) throw new Error("Token response did not include proof metadata.");
      setAdmission({ serverUrl: body.serverUrl, token: body.token, proof: body.proof });
    } catch (error) {
      console.error("[call-experience] could not start the call", error);
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
      finishCallReview(
        source.current.turns,
        source.current.capturedCommitment,
        source.current.chaptersReferenced,
      ),
    );
    leaveCall();
  }, [leaveCall]);

  const rememberTurns = useCallback((turns: TranscriptTurn[]) => {
    source.current.turns = turns;
  }, []);

  const rememberCommitment = useCallback((text: string) => {
    source.current.capturedCommitment = text;
  }, []);

  const rememberChapters = useCallback((chapters: ReferencedChapter[]) => {
    source.current.chaptersReferenced = chapters;
  }, []);

  const disconnectNotion = useCallback(async () => {
    setNotionBusy(true);
    setNotionFailure(null);
    try {
      await fetch("/api/notion", { method: "DELETE" });
      setNotion(EMPTY_NOTION);
    } catch (error) {
      console.error("[call-experience] Notion disconnect failed", error);
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
      audio={true}
      video={false}
      onDisconnected={leaveCall}
      onError={(error) => {
        console.error("[call-experience] room error", error);
        setCallFailure(callRecoveryMessage("room", error));
        leaveCall();
      }}
      className={`shell live-shell${proofMode ? " proof-shell" : ""}`}
    >
      <RoomAudioRenderer />
      <CallView
        reviewDestination={notion.connected ? notion.selectedDatabase.name : null}
        onTurnsChange={rememberTurns}
        onCommitment={rememberCommitment}
        onChaptersChange={rememberChapters}
        onEndCall={completeCall}
        proofAdmission={proofMode ? admission.proof : null}
      />
    </LiveKitRoom>
  );
}
