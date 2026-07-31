import { describe, expect, it } from "vitest";

import { DraftRateLimiter, createReviewPermit, verifyReviewPermit } from "./review-access";

describe("paid review draft access", () => {
  it("accepts a recent server-signed call permit", () => {
    const permit = createReviewPermit("test-secret", 1_000);

    expect(verifyReviewPermit(permit, "test-secret", 1_000 + 10 * 60_000)).toBe(true);
  });

  it("rejects changed, expired, and wrong-deployment permits", () => {
    const permit = createReviewPermit("test-secret", 1_000);

    expect(verifyReviewPermit(`${permit}changed`, "test-secret", 2_000)).toBe(false);
    expect(verifyReviewPermit(permit, "other-secret", 2_000)).toBe(false);
    expect(verifyReviewPermit(permit, "test-secret", 1_000 + 31 * 60_000)).toBe(false);
  });

  it("limits repeated drafts from one network address", () => {
    const limiter = new DraftRateLimiter(2, 60_000);

    expect(limiter.take("203.0.113.4", 1_000)).toBe(true);
    expect(limiter.take("203.0.113.4", 2_000)).toBe(true);
    expect(limiter.take("203.0.113.4", 3_000)).toBe(false);
    expect(limiter.take("203.0.113.5", 3_000)).toBe(true);
    expect(limiter.take("203.0.113.4", 62_000)).toBe(true);
  });
});
