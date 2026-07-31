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
  callFailure,
  notionFailure,
  notion,
  notionBusy,
  onChooseDatabase,
  onDisconnectNotion,
}: {
  onStart: () => void;
  connecting: boolean;
  callFailure: string | null;
  notionFailure: string | null;
  notion: NotionConnection;
  notionBusy: boolean;
  onChooseDatabase: (id: string) => void;
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
    <main className="shell start-shell og-start-shell">
      <header className="masthead">
        <div className="brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="mark"
            src="/epictetus.png"
            alt=""
            width={512}
            height={512}
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

        {callFailure && (
          <p className="failure" role="alert">
            {callFailure}
          </p>
        )}

        <div className="notion-connect">
          {notionBusy ? (
            <p className="notion-status" aria-live="polite">
              Checking Notion connection…
            </p>
          ) : !notion.connected ? (
            <>
              <a className="quiet button-link" href="/api/notion/connect">
                Connect Notion
              </a>
              <p className="hint">
                Optional. Connect the workspace where you want completed reviews saved.
                Epictetus never reads your Notion pages during a call.
              </p>
            </>
          ) : (
            <>
              <p className="connection-line">
                <span className="connection-dot" aria-hidden="true" />
                Connected to {notion.workspaceName}
              </p>
              <label htmlFor="review-database">Evening reviews database</label>
              <select
                id="review-database"
                value={notion.selectedDatabase?.id ?? ""}
                onChange={(event) => onChooseDatabase(event.target.value)}
                disabled={notionBusy}
              >
                <option value="">Choose a database…</option>
                {notion.databases.map((database) => (
                  <option key={database.id} value={database.id}>
                    {database.name}
                  </option>
                ))}
              </select>
              <button className="quiet" type="button" onClick={onDisconnectNotion}>
                Disconnect Notion
              </button>
              {notion.databases.length === 0 && (
                <p className="hint">
                  No databases are shared with this connection yet. Reconnect and choose
                  the page that contains your reviews database.
                </p>
              )}
            </>
          )}

          {notionFailure && (
            <p className="failure notion-failure" role="alert">
              {notionFailure}
            </p>
          )}
        </div>
      </form>
    </main>
  );
}

export type NotionConnection = {
  connected: boolean;
  workspaceName?: string;
  databases: { id: string; name: string }[];
  selectedDatabase?: { id: string; name: string; titleProperty: string } | null;
};
