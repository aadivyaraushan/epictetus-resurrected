"use client";

/**
 * What he goes off and does mid-conversation.
 *
 * Input:  messages on the "epictetus.activity" data topic, published by each
 *         tool before it runs (agent/persona/epictetus_agent.py)
 * Output: a short running list -- "looked up: what a smartphone is"
 *
 * Worth showing for two reasons. A tool call takes a second or two of silence,
 * and silence with a visible reason for it reads as thinking rather than as a
 * broken call. And the brief grades tool use, so it should be visible that it
 * happened rather than inferred from what he says afterwards.
 */

import { useDataChannel } from "@livekit/components-react";
import { useCallback, useState } from "react";

import { readCommitmentActivity } from "../../review/flow/call-review-flow";

const TOPIC = "epictetus.activity";
// Old entries are scrollback nobody reads; this is a live indicator.
const KEEP = 6;

type Deed = { action: string; detail: string; kind?: string; at: number };

export function ToolActivity({ onCommitment }: { onCommitment: (text: string) => void }) {
  const [deeds, setDeeds] = useState<Deed[]>([]);

  const receive = useCallback((message: { payload: Uint8Array }) => {
    try {
      const body = JSON.parse(new TextDecoder().decode(message.payload));
      if (typeof body?.action !== "string") return;
      const deed: Deed = {
        action: body.action,
        detail: typeof body.detail === "string" ? body.detail : "",
        kind: typeof body.kind === "string" ? body.kind : undefined,
        at: Date.now(),
      };
      const commitment = readCommitmentActivity(body);
      if (commitment) onCommitment(commitment);
      setDeeds((previous) => [...previous, deed].slice(-KEEP));
    } catch (error) {
      console.error("[tool-activity] could not read an activity message", error);
    }
  }, [onCommitment]);

  useDataChannel(TOPIC, receive);

  if (deeds.length === 0) return null;

  return (
    <section className="column" style={{ flex: "0 0 auto" }}>
      <h2>What he is doing</h2>
      <div>
        {deeds.map((deed) => (
          <div className="deed" key={deed.at}>
            <span className="mark">&#8250;</span>
            <span>
              {deed.action}
              {deed.detail && <>: {deed.detail}</>}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
