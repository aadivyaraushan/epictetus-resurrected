"use client";

/**
 * What you see before the call: one line of his, an explanation, and a button.
 *
 * The passphrase field is deliberately unobtrusive and honest about what it
 * does. Hiding it would be security by obscurity, and the design is described in
 * a public README anyway -- so it says plainly that it exists and that leaving it
 * empty is the normal case.
 */

import { useState, type FormEvent } from "react";

export function StartScreen({
  onStart,
  connecting,
  failure,
}: {
  onStart: (passphrase: string) => void;
  connecting: boolean;
  failure: string | null;
}) {
  const [passphrase, setPassphrase] = useState("");
  const [showPassphrase, setShowPassphrase] = useState(false);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!connecting) onStart(passphrase);
  }

  return (
    <main className="shell">
      <header className="masthead">
        <div>
          <h1>Epictetus, Resurrected</h1>
          <p className="sub">Nicopolis, c. 108 &mdash; and now</p>
        </div>
        <span className="badge">grounded in the Discourses</span>
      </header>

      <form className="start" onSubmit={submit}>
        <blockquote>
          &ldquo;Men are disturbed not by the things which happen, but by the
          opinions about the things.&rdquo;
          <cite>Discourses, Book I</cite>
        </blockquote>

        <p className="lede">
          Speak to him about something that is actually bothering you. He will ask
          before he advises. Everything he says is checked against his own
          recorded teaching first, and the passages he drew on appear beside the
          conversation as he speaks.
        </p>

        <button className="primary" type="submit" disabled={connecting}>
          {connecting ? "Waking him…" : "Start Call"}
        </button>

        <div className="passphrase">
          <button
            type="button"
            className="quiet"
            aria-pressed={showPassphrase}
            onClick={() => setShowPassphrase((shown) => !shown)}
          >
            {showPassphrase ? "Hide passphrase" : "I have a passphrase"}
          </button>

          {showPassphrase && (
            <>
              <input
                type="password"
                value={passphrase}
                onChange={(event) => setPassphrase(event.target.value)}
                placeholder="passphrase"
                aria-label="Passphrase for the live personal backend"
                autoComplete="off"
              />
              <p className="hint">
                Leave this empty. Without it, his tools read a seeded set of
                notes &mdash; which is what a visitor is meant to see. The
                passphrase only exists so the author can point the same deployed
                link at real notes without putting anyone else&rsquo;s link near
                it.
              </p>
            </>
          )}
        </div>

        {failure && (
          <p className="failure" role="alert">
            {failure}
          </p>
        )}
      </form>

      <footer className="controls">
        <span className="status">
          Your microphone is only used while a call is running.
        </span>
      </footer>
    </main>
  );
}
