"use client";

/**
 * What you see before the call: one line of his, an explanation, and a button.
 *
 * A Notion connection is optional for the call and required only when the
 * caller chooses to save their completed review.
 */

import { useEffect, useState, type FormEvent } from "react";

import { DISCOURSES_QUOTES, pickDiscourseQuote } from "./quotes";

export function StartScreen({
  onStart,
  connecting,
  failure,
  notion,
  onDisconnectNotion,
}: {
  onStart: () => void;
  connecting: boolean;
  failure: string | null;
  notion: NotionConnection;
  onDisconnectNotion: () => void;
}) {
  const [frontQuote, setFrontQuote] = useState(DISCOURSES_QUOTES[0]);

  useEffect(() => {
    setFrontQuote(pickDiscourseQuote(Math.random()));
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!connecting) onStart();
  }

  return (
    <main className="shell">
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
      </header>

      <form className="start" onSubmit={submit}>
        <blockquote>
          &ldquo;{frontQuote.text}&rdquo;
          <cite>{frontQuote.citation}</cite>
        </blockquote>

        <p className="lede">
          Speak to him about something that is actually bothering you. He will ask
          before he advises. Everything he says is checked against his own
          recorded teaching first, and the passages he drew on appear beside the
          conversation as he speaks. He also keeps a written record of the call
          as it goes &mdash; the way Arrian kept one of his &mdash; so sessions
          end with an editable transcript, summary, and next step. Nothing is
          saved to Notion until you review it and press Save.
        </p>

        <button className="primary" type="submit" disabled={connecting}>
          {connecting ? "Waking him…" : "Start Call"}
        </button>

        <div className="notion-connect">
          {!notion.connected ? (
            <>
              <a className="quiet button-link" href="/api/notion/connect">
                {notion.reconnectMessage ? "Reconnect Notion" : "Connect Notion"}
              </a>
              <p className="hint">
                {notion.reconnectMessage ?? (
                  <>
                    Optional. Connect the workspace where you want completed reviews saved.
                    Epictetus never reads your Notion pages during a call.
                  </>
                )}
              </p>
            </>
          ) : (
            <>
              <p className="connection-line">
                <span className="connection-dot" aria-hidden="true" />
                Connected to {notion.workspaceName}
              </p>
              <p className="hint">
                Evening reviews save to <strong>{notion.selectedDatabase.name}</strong>.
              </p>
              <button className="quiet" type="button" onClick={onDisconnectNotion}>
                Disconnect Notion
              </button>
            </>
          )}
        </div>

        {failure && (
          <p className="failure" role="alert">
            {failure}
          </p>
        )}
      </form>
    </main>
  );
}

export type NotionConnection =
  | { connected: false; reconnectMessage?: string }
  | {
      connected: true;
      workspaceName: string;
      selectedDatabase: { id: string; name: string; titleProperty: string };
    };
