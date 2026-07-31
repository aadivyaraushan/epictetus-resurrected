import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

const PERMIT_LIFETIME_MS = 30 * 60_000;

function signature(payload: string, secret: string) {
  if (!secret) throw new Error("REVIEW_SESSION_SECRET is missing.");
  return createHmac("sha256", secret)
    .update(`review-permit:${payload}`)
    .digest("base64url");
}

export function createReviewPermit(secret: string, now = Date.now()) {
  const payload = `${now}.${randomBytes(16).toString("base64url")}`;
  return `${payload}.${signature(payload, secret)}`;
}

export function verifyReviewPermit(value: string, secret: string, now = Date.now()) {
  try {
    const [issuedRaw, nonce, received] = value.split(".");
    if (!issuedRaw || !nonce || !received) return false;
    const issued = Number(issuedRaw);
    if (!Number.isFinite(issued) || issued > now || now - issued > PERMIT_LIFETIME_MS) {
      return false;
    }
    const expected = signature(`${issuedRaw}.${nonce}`, secret);
    const left = Buffer.from(received);
    const right = Buffer.from(expected);
    return left.length === right.length && timingSafeEqual(left, right);
  } catch {
    return false;
  }
}

export class DraftRateLimiter {
  private attempts = new Map<string, number[]>();

  constructor(
    private readonly limit: number,
    private readonly windowMs: number,
  ) {}

  take(key: string, now = Date.now()) {
    const recent = (this.attempts.get(key) ?? []).filter(
      (timestamp) => now - timestamp < this.windowMs,
    );
    if (recent.length >= this.limit) {
      this.attempts.set(key, recent);
      return false;
    }
    recent.push(now);
    this.attempts.set(key, recent);
    return true;
  }
}
