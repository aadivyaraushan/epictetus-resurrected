"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

import { formatTranscript, reviewTitle, type CallReviewSource } from "./review-data";

export function ReviewScreen({
  source,
  databaseName,
  onNewCall,
}: {
  source: CallReviewSource;
  databaseName: string | null;
  onNewCall: () => void;
}) {
  const originalTranscript = useMemo(() => formatTranscript(source.turns), [source.turns]);
  const [title, setTitle] = useState(() => reviewTitle());
  const [summary, setSummary] = useState("");
  const [nextStep, setNextStep] = useState(source.capturedCommitment);
  const [transcript, setTranscript] = useState(originalTranscript);
  const [drafting, setDrafting] = useState(Boolean(originalTranscript));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    if (!originalTranscript) return;
    const controller = new AbortController();
    async function draft() {
      try {
        const response = await fetch("/api/review/draft", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transcript: originalTranscript,
            capturedCommitment: source.capturedCommitment,
          }),
          signal: controller.signal,
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body?.error ?? "Could not draft the review.");
        setSummary(body.summary ?? "");
        setNextStep(body.nextStep ?? source.capturedCommitment);
      } catch (error) {
        if (controller.signal.aborted) return;
        console.error("[review-screen] draft failed", error);
        setFailure("The automatic draft failed. You can still write and save the review.");
      } finally {
        if (!controller.signal.aborted) setDrafting(false);
      }
    }
    void draft();
    return () => controller.abort();
  }, [originalTranscript, source.capturedCommitment]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFailure(null);
    try {
      const response = await fetch("/api/review/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          completed: true,
          title,
          summary,
          nextStep,
          transcript,
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body?.error ?? "Could not save the review.");
      setSaved(true);
    } catch (error) {
      console.error("[review-screen] save failed", error);
      setFailure(error instanceof Error ? error.message : "Could not save the review.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="shell review-shell">
      <header className="masthead">
        <div className="brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="mark" src="/epictetus.png" alt="" width={512} height={512} />
          <div>
            <h1>Evening Review</h1>
            <p className="sub">Read it once. Change anything that is not yours.</p>
          </div>
        </div>
        <span className="badge">call complete</span>
      </header>

      <form className="review-form" onSubmit={save}>
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>
          Summary {drafting && <span className="drafting">drafting…</span>}
          <textarea
            rows={6}
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            placeholder={drafting ? "Drafting from the call…" : "What became clearer?"}
          />
        </label>
        <label>
          Next step
          <textarea
            rows={3}
            value={nextStep}
            onChange={(event) => setNextStep(event.target.value)}
            placeholder="Leave blank if you made no commitment."
          />
        </label>
        <label>
          Transcript
          <textarea
            className="review-transcript"
            rows={14}
            value={transcript}
            onChange={(event) => setTranscript(event.target.value)}
          />
        </label>

        {failure && <p className="failure" role="alert">{failure}</p>}
        {saved && <p className="saved" role="status">Saved to {databaseName}.</p>}

        <div className="review-actions">
          <button className="quiet" type="button" onClick={onNewCall}>
            New call
          </button>
          {databaseName ? (
            <button className="primary" type="submit" disabled={saving || saved || drafting}>
              {saved ? "Saved" : saving ? "Saving…" : `Save to ${databaseName}`}
            </button>
          ) : (
            <span className="hint">Connect Notion before your next call to save reviews.</span>
          )}
        </div>
      </form>
    </main>
  );
}
