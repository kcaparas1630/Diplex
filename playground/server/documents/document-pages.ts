/** Gives the viewer a range of a document's pages: each page's size and a freshly signed URL for its image (ADR 001 §5). */
import type { S3Client } from "@aws-sdk/client-s3";

import { findOwnedDocumentRow, type SqlQueries } from "../database";
import { SIGNED_URL_SECONDS, documentKeys, signGetUrl } from "../storage";

/** What reading a document's pages needs: the database and the client that signs URLs browsers can reach. */
export interface PageSource {
  database: SqlQueries;
  signingClient: S3Client;
  bucketName: string;
}

/** One page as the viewer gets it: its number, its size in points, and a URL that works for SIGNED_URL_SECONDS. */
export interface ViewerPage {
  index: number;
  width: number;
  height: number;
  url: string;
}

/** The answer for one range: the document's page count, the pages asked for, and when their URLs stop working. */
export interface PageRange {
  pageCount: number;
  pages: ViewerPage[];
  expiresAt: string;
}

export const DEFAULT_PAGES_PER_REQUEST = 10; // ADR 001 §5: sign in batches of about 10 as the user scrolls
const MAX_PAGES_PER_REQUEST = 50;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** Sign URLs for pages firstPage onwards (1-based), clamped to the document; null unless the owner asks for their own document. */
export async function getDocumentPages(
  store: PageSource,
  ownerId: string | undefined,
  documentId: string,
  firstPage: number,
  requestedCount: number,
): Promise<PageRange | null> {
  if (!ownerId || !UUID_PATTERN.test(documentId)) {
    return null;
  }
  const documentRow = await findOwnedDocumentRow(store.database, documentId, ownerId);
  if (!documentRow) {
    return null; // missing, deleted and someone else's look the same, so IDs can't be probed
  }
  const startOffset = Math.max(1, Math.floor(firstPage) || 1) - 1;
  const pageCount = Math.min(MAX_PAGES_PER_REQUEST, Math.max(1, Math.floor(requestedCount) || DEFAULT_PAGES_PER_REQUEST));
  const requestedPages = documentRow.pageSizes.slice(startOffset, startOffset + pageCount);
  const signedAt = Date.now();
  const pages = await Promise.all(
    requestedPages.map(async (pageSize) => ({
      ...pageSize,
      url: await signGetUrl(store.signingClient, store.bucketName, documentKeys.page(documentRow.folder, pageSize.index)),
    })),
  );
  return { pageCount: documentRow.pageSizes.length, pages, expiresAt: new Date(signedAt + SIGNED_URL_SECONDS * 1000).toISOString() };
}
