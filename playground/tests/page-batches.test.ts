/** Tests the viewer's batching: which batches to ask for, reusing URLs until shortly before they expire. */
import { describe, expect, it } from "vitest";

import { batchStartFor, batchesToRequest, needsSigning, type SignedPageUrl } from "../viewer/page-batches";

const NOW = 1_800_000_000_000;

describe("batchStartFor", () => {
  it("groups pages 1-10, 11-20 and so on", () => {
    expect([1, 10, 11, 20, 21, 95].map(batchStartFor)).toEqual([1, 1, 11, 11, 21, 91]);
  });
});

describe("needsSigning", () => {
  it("asks for a URL the page doesn't have", () => {
    expect(needsSigning(undefined, NOW)).toBe(true);
  });

  it("reuses a URL for its lifetime, until a minute before it expires", () => {
    expect(needsSigning({ url: "u", expiresAtMilliseconds: NOW + 10 * 60_000 }, NOW)).toBe(false);
    expect(needsSigning({ url: "u", expiresAtMilliseconds: NOW + 30_000 }, NOW)).toBe(true);
  });
});

describe("batchesToRequest", () => {
  it("asks once per batch the visible pages need, skipping pages with good URLs and batches already on their way", () => {
    const signedUrls = new Map<number, SignedPageUrl>([
      [1, { url: "a", expiresAtMilliseconds: NOW + 600_000 }],
      [2, { url: "b", expiresAtMilliseconds: NOW + 600_000 }],
      [12, { url: "c", expiresAtMilliseconds: NOW + 10_000 }],
    ]);

    expect(batchesToRequest([1, 2, 12, 13, 25], signedUrls, new Set([21]), NOW)).toEqual([11]);
    expect(batchesToRequest([1, 2], signedUrls, new Set(), NOW)).toEqual([]);
    expect(batchesToRequest([40, 3, 31], new Map(), new Set(), NOW)).toEqual([1, 31]);
  });
});
