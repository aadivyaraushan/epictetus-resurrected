import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function read(path: string) {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

describe("the proof route keeps the current call and review behavior", () => {
  it("uses one shared call experience for the normal and proof routes", () => {
    const publicPage = read("app/page.tsx");
    const proofPage = read("app/proof/page.tsx");
    const experience = read("call/experience/call-experience.tsx");

    expect(publicPage).toContain("<CallExperience />");
    expect(publicPage).not.toContain("proofMode");
    expect(proofPage).toContain("<CallExperience proofMode />");
    expect(experience).toContain("proofMode?: boolean");
  });

  it("keeps chapter evidence from the call through the completed review", () => {
    const experience = read("call/experience/call-experience.tsx");
    const callView = read("call/live/call-view.tsx");
    const timeline = read("call/proof/proof-timeline.tsx");

    expect(experience).toContain("chaptersReferenced: []");
    expect(experience).toContain("source.current.chaptersReferenced");
    expect(experience).toContain("onChaptersChange={rememberChapters}");
    expect(experience).toContain("finishCallReview(");
    expect(callView).toContain("onChaptersChange={onChaptersChange}");
    expect(timeline).toContain("mergeReferencedChapters");
  });

  it("gives only proof mode the safe admission facts and combined timeline", () => {
    const experience = read("call/experience/call-experience.tsx");
    const callView = read("call/live/call-view.tsx");
    const timeline = read("call/proof/proof-timeline.tsx");

    expect(experience).toContain(
      "proofAdmission={proofMode && roomConnected ? admission.proof : null}",
    );
    expect(callView).toContain("proofAdmission");
    expect(timeline).toContain("Proof timeline");
    expect(timeline).toContain("Room admitted");
  });

  it("does not call a token response an admitted room before LiveKit connects", () => {
    const experience = read("call/experience/call-experience.tsx");

    expect(experience).toContain("onConnected={() => setRoomConnected(true)}");
    expect(experience).toContain(
      "proofAdmission={proofMode && roomConnected ? admission.proof : null}",
    );
  });
});
