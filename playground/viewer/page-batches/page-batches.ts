/** Decides which pages the viewer must ask signed URLs for: batches of 10, each URL reused until shortly before it expires. */

/** A page's signed URL and when it stops working, in epoch milliseconds. */
export interface SignedPageUrl {
  url: string;
  expiresAtMilliseconds: number;
}

export const PAGES_PER_BATCH = 10; // ADR 001 §5: sign about 10 pages at a time as the user scrolls
export const RENEW_BEFORE_EXPIRY_MILLISECONDS = 60_000; // ask again a minute early, so an image never loads from a dead URL

/** The first page (1-based) of the batch that holds this page: pages 1-10 are batch 1, 11-20 batch 11, and so on. */
export function batchStartFor(pageIndex: number): number {
  return Math.floor((pageIndex - 1) / PAGES_PER_BATCH) * PAGES_PER_BATCH + 1;
}

/** Tell whether a page needs a (new) signed URL: it has none, or the one it has is about to expire. */
export function needsSigning(signedUrl: SignedPageUrl | undefined, nowMilliseconds: number): boolean {
  return !signedUrl || signedUrl.expiresAtMilliseconds - RENEW_BEFORE_EXPIRY_MILLISECONDS <= nowMilliseconds;
}

/** The batches to ask for so every visible page has a usable URL, skipping batches already on their way. */
export function batchesToRequest(
  visiblePages: number[],
  signedUrls: ReadonlyMap<number, SignedPageUrl>,
  batchesInFlight: ReadonlySet<number>,
  nowMilliseconds: number,
): number[] {
  const batchStarts = visiblePages.filter((pageIndex) => needsSigning(signedUrls.get(pageIndex), nowMilliseconds)).map(batchStartFor);
  return [...new Set(batchStarts)].filter((batchStart) => !batchesInFlight.has(batchStart)).sort((first, second) => first - second);
}
