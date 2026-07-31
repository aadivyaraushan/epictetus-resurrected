"use client";

/**
 * The passages behind what he just said.
 *
 * Input:  messages on the "epictetus.sources" data topic, published by the worker
 *         every turn it retrieves something (agent/grounding/turn_rag.py)
 * Output: the book, chapter, title and text of each passage it used
 *
 * This panel is the honest half of the persona. He speaks without citing --
 * "as I wrote in Book II" is not something a person says about their own
 * lectures -- so the citation has to appear somewhere, and it appears here.
 *
 * An empty list is a real message and clears the panel. The worker sends it on
 * turns it decided not to ground, so stale passages never sit beside an answer
 * that did not come from them.
 */

import { useDataChannel } from "@livekit/components-react";
import { useCallback, useState } from "react";

const TOPIC = "epictetus.sources";

type Source = {
  citation: string;
  title: string;
  text: string;
  score: number;
};

export function SourcePanel() {
  const [sources, setSources] = useState<Source[]>([]);
  const [everGrounded, setEverGrounded] = useState(false);

  const receive = useCallback((message: { payload: Uint8Array }) => {
    try {
      const body = JSON.parse(new TextDecoder().decode(message.payload));
      const incoming: Source[] = Array.isArray(body?.sources) ? body.sources : [];
      setSources(incoming);
      if (incoming.length > 0) setEverGrounded(true);
    } catch (error) {
      // A malformed message should cost the panel, not the call.
      console.error("[source-panel] could not read a sources message", error);
    }
  }, []);

  useDataChannel(TOPIC, receive);

  return (
    <section className="column">
      <h2>What he is drawing on</h2>
      <div className="scroller">
        {sources.length === 0 ? (
          <p className="empty">
            {everGrounded
              ? "Nothing from the Discourses for that one — he is answering from himself."
              : "Ask him something he would have had a view on, and the passages he used will appear here."}
          </p>
        ) : (
          sources.map((source, index) => (
            <article className="source" key={`${source.citation}-${index}`}>
              <div className="cite">{source.citation}</div>
              <div className="title">{source.title}</div>
              <p className="quote">{source.text}</p>
              <div className="score">similarity {source.score.toFixed(3)}</div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
