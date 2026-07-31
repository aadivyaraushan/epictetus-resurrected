import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { DISCOURSES_QUOTES, pickDiscourseQuote } from "./quotes";

describe("front-page Discourses quotes", () => {
  it("offers a real assortment across all four books", () => {
    expect(DISCOURSES_QUOTES.length).toBeGreaterThanOrEqual(12);
    expect(new Set(DISCOURSES_QUOTES.map((quote) => quote.book))).toEqual(
      new Set([1, 2, 3, 4]),
    );
  });

  it("keeps every quote attributable to a chapter", () => {
    for (const quote of DISCOURSES_QUOTES) {
      expect(quote.text.trim().length).toBeGreaterThan(20);
      expect(quote.chapter).toBeGreaterThan(0);
      expect(quote.citation).toBe(
        `Discourses, Book ${quote.book}, Chapter ${quote.chapter}`,
      );
      const chapter = readFileSync(
        resolve(
          process.cwd(),
          `../corpus/source/b${quote.book}c${String(quote.chapter).padStart(2, "0")}.txt`,
        ),
        "utf8",
      );
      expect(chapter).toContain(quote.text);
    }
  });

  it("maps the random value over the complete set", () => {
    expect(pickDiscourseQuote(0)).toBe(DISCOURSES_QUOTES[0]);
    expect(pickDiscourseQuote(0.999999)).toBe(DISCOURSES_QUOTES.at(-1));
  });

  it("falls back safely if a random source returns an invalid value", () => {
    expect(pickDiscourseQuote(Number.NaN)).toBe(DISCOURSES_QUOTES[0]);
    expect(pickDiscourseQuote(1)).toBe(DISCOURSES_QUOTES[0]);
  });
});
