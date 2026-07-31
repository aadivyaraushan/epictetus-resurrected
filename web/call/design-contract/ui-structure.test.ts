import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function read(path: string) {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

describe("the three call stages preserve their approved design contracts", () => {
  it("restores the original centered home while keeping saving optional", () => {
    const start = read("call/start-screen/start-screen.tsx");
    const css = read("app/globals.css");

    expect(start).toContain('className="shell start-shell og-start-shell"');
    expect(start).toContain('className="masthead"');
    expect(start).toContain('className="brand"');
    expect(start).toContain('className="mark"');
    expect(start).toContain('className="start"');
    expect(start).not.toContain('className="start-stage"');
    expect(start).not.toContain('className="start-portrait"');
    expect(start).toContain("Checking Notion connection…");
    expect(css).toMatch(/\.og-start-shell \.start\s*\{[^}]*justify-content: center;[^}]*align-items: center;[^}]*text-align: center;/);
  });

  it("places call and Notion alerts inside their own recovery sections", () => {
    const page = read("app/page.tsx");
    const start = read("call/start-screen/start-screen.tsx");

    expect(page).toContain("callFailure={callFailure}");
    expect(page).toContain("notionFailure={notionFailure}");
    expect(start).toContain("callFailure: string | null");
    expect(start).toContain("notionFailure: string | null");
    expect(start).toMatch(/className="primary"[\s\S]*\{callFailure && \(/);
    expect(start).toMatch(/className="notion-connect"[\s\S]*\{notionFailure && \(/);
  });

  it("keeps the live conversation primary beside one evidence rail", () => {
    const live = read("call/live/call-view.tsx");

    expect(live).toContain('className="live-masthead"');
    expect(live).toContain('className="call live-layout"');
    expect(live).toContain('className="evidence-rail"');
    expect(live).toContain('className="controls live-controls"');
  });

  it("gives the completed review a context rail and an emphasized next step", () => {
    const review = read("call/review/review-screen.tsx");

    expect(review).toContain('className="review-layout"');
    expect(review).toContain('className="review-context"');
    expect(review).toContain('className="next-step-field"');
    expect(review).toContain("Your record");
  });

  it("defines the shared surfaces, reading type, focus ring, and mobile frame", () => {
    const css = read("app/globals.css");

    expect(css).toContain("--stone-0: #11100d");
    expect(css).toContain("--font-reading:");
    expect(css).toContain("outline: 2px solid var(--lamp-bright)");
    expect(css).toContain("@media (max-width: 899px)");
    expect(css).toContain("prefers-reduced-motion: reduce");
  });

  it("keeps the narrow review state and End Call labels on one line", () => {
    const css = read("app/globals.css");

    expect(css).toMatch(/\.review-masthead \.destination\s*\{[^}]*white-space: nowrap;/);
    expect(css).toMatch(/\.live-controls \.danger\s*\{[^}]*white-space: nowrap;/);
    expect(css).toMatch(/\.review-masthead \.destination\s*\{[^}]*flex-basis: 100%;/);
  });

  it("confines the desktop live stage while both reading columns scroll independently", () => {
    const page = read("app/page.tsx");
    const css = read("app/globals.css");

    expect(page).toContain('className="shell live-shell"');
    expect(css).toMatch(/@media \(min-width: 900px\)[\s\S]*\.live-shell\s*\{[^}]*height: 100dvh;[^}]*overflow: hidden;/);
    expect(css).toMatch(/@media \(min-width: 900px\)[\s\S]*\.live-shell \.live-layout\s*\{[^}]*min-height: 0;[^}]*overflow: hidden;/);
    expect(css).toMatch(/@media \(min-width: 900px\)[\s\S]*\.live-shell \.scroller\s*\{[^}]*min-height: 0;[^}]*overflow-y: auto;/);
    expect(css).toContain(
      "A simple white-line portrait on transparency, kept legible at logo size.",
    );
  });
});
