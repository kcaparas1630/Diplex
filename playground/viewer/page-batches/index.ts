/** Which pages the viewer asks signed URLs for, and when: batches of 10, renewed shortly before they expire. */
export { PAGES_PER_BATCH, RENEW_BEFORE_EXPIRY_MILLISECONDS, batchStartFor, batchesToRequest, needsSigning } from "./page-batches";
export type { SignedPageUrl } from "./page-batches";
