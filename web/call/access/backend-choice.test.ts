/**
 * The passphrase check, tested first because it is the one piece of this project
 * where being wrong has a cost outside the demo.
 *
 * The agent's personal tools have two backends: a seeded demo week that everyone
 * gets, and a live one wired to the author's real calendar and notes. This
 * function is the only thing standing between a stranger and the live one, and
 * the deployed link is public for 14 days while a README and a video describe
 * exactly how it works. So the tests below are mostly about the ways it should
 * refuse.
 */

import { describe, expect, it } from "vitest";

import { chooseBackend } from "./backend-choice";

describe("chooseBackend", () => {
  it("unlocks the live backend for the exact passphrase", () => {
    expect(chooseBackend("open sesame", "open sesame")).toBe("live");
  });

  it("falls back to demo for a wrong passphrase", () => {
    expect(chooseBackend("guess", "open sesame")).toBe("demo");
  });

  it("falls back to demo when the caller sends nothing", () => {
    expect(chooseBackend(undefined, "open sesame")).toBe("demo");
    expect(chooseBackend("", "open sesame")).toBe("demo");
  });

  // Fail closed. An unset server secret is a misconfigured deployment, and the
  // wrong way to handle it is to let an empty passphrase match an empty secret.
  it("never unlocks live when the server has no passphrase configured", () => {
    for (const secret of [undefined, "", "   "]) {
      expect(chooseBackend("", secret)).toBe("demo");
      expect(chooseBackend("anything", secret)).toBe("demo");
      expect(chooseBackend(secret, secret)).toBe("demo");
    }
  });

  it("ignores surrounding whitespace, which a phone keyboard adds on its own", () => {
    expect(chooseBackend("  open sesame  ", "open sesame")).toBe("live");
  });

  it("is case- and character-exact otherwise", () => {
    expect(chooseBackend("Open Sesame", "open sesame")).toBe("demo");
    expect(chooseBackend("open sesam", "open sesame")).toBe("demo");
    expect(chooseBackend("open sesamee", "open sesame")).toBe("demo");
  });

  it("does not accept a prefix of the passphrase", () => {
    expect(chooseBackend("open", "open sesame")).toBe("demo");
  });

  it("survives a caller sending something that is not a string", () => {
    for (const junk of [null, 42, {}, [], true]) {
      expect(chooseBackend(junk as unknown as string, "open sesame")).toBe("demo");
    }
  });
});
