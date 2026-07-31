/**
 * Decide which backend the agent's personal tools should talk to.
 *
 * Input:  the passphrase the caller typed on the start screen, and the secret
 *         the server was configured with
 * Output: "live" or "demo"
 *
 * This runs on the server, inside the token endpoint, and never in the browser.
 * The verdict is written into the signed access token, so the worker can read it
 * but the caller cannot change it -- the caller never handles the verdict, only
 * the passphrase that produced it.
 *
 * Why a passphrase and not a name. The first design checked the caller's display
 * name against the author's. That is not a credential: this project is described
 * in a public README and a public video, and the deployed link stays up for two
 * weeks, so anyone who read either could type that name and reach a real
 * calendar and real notes. A secret compared on the server is the smallest thing
 * that actually works.
 *
 * Demo is the default and every failure path leads to it. Nothing here throws.
 */

import { createHash, timingSafeEqual } from "node:crypto";

export type Backend = "live" | "demo";

/** Compare without letting the time taken reveal how much of the guess matched.
 *
 * The two strings are hashed first so the comparison always runs over 32 bytes.
 * Comparing the raw strings would need them to be the same length, and handling
 * a length mismatch separately would leak the passphrase's length to anyone
 * timing the endpoint.
 */
function sameSecret(a: string, b: string): boolean {
  const digest = (value: string) => createHash("sha256").update(value, "utf8").digest();
  return timingSafeEqual(digest(a), digest(b));
}

export function chooseBackend(
  offered: string | undefined,
  configured: string | undefined,
): Backend {
  // Fail closed. No secret configured means the live backend is unreachable,
  // rather than reachable by sending the empty string.
  const expected = typeof configured === "string" ? configured.trim() : "";
  if (!expected) return "demo";

  // A caller can put anything in a JSON body, including a number or an object.
  const given = typeof offered === "string" ? offered.trim() : "";
  if (!given) return "demo";

  return sameSecret(given, expected) ? "live" : "demo";
}
