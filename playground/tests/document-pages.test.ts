/** Tests signing a range of pages for the viewer: owner only, clamped to the document, URLs that expire in 30 minutes. */
import { S3Client } from "@aws-sdk/client-s3";
import { describe, expect, it } from "vitest";

import { getDocumentPages, type PageSource } from "../server/documents";

const OWNER = "0b5c2f7e-8a1d-4c3e-9f20-6d1a2b3c4d5e";
const DOCUMENT_ID = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d";
const PAGE_SIZES = Array.from({ length: 25 }, (_, pageOffset) => ({ index: pageOffset + 1, width: 612, height: 792 }));

/** A page source whose database holds one document of 25 pages for OWNER, signing with the browser-facing endpoint. */
function standInPageSource(): PageSource {
  return {
    database: {
      query: async (_queryText: string, queryValues?: unknown[]) => ({
        rows:
          queryValues?.[0] === DOCUMENT_ID && queryValues?.[1] === OWNER
            ? [{ id: DOCUMENT_ID, owner_id: OWNER, file_name: "a.pdf", folder: `playground/${OWNER}/${DOCUMENT_ID}`, source_type: "pdf", page_sizes: PAGE_SIZES, created_at: new Date(), deleted_at: null }]
            : [],
      }),
    },
    signingClient: new S3Client({
      endpoint: "http://localhost:9000",
      region: "us-east-1",
      forcePathStyle: true,
      credentials: { accessKeyId: "playground", secretAccessKey: "playground-secret" },
    }),
    bucketName: "playground-documents",
  };
}

describe("getDocumentPages", () => {
  it("signs the requested pages for the browser's endpoint, valid for 30 minutes, with their sizes", async () => {
    const pageRange = await getDocumentPages(standInPageSource(), OWNER, DOCUMENT_ID, 11, 10);

    expect(pageRange?.pageCount).toBe(25);
    expect(pageRange?.pages.map((page) => page.index)).toEqual([11, 12, 13, 14, 15, 16, 17, 18, 19, 20]);
    const firstUrl = new URL(String(pageRange?.pages[0].url));
    expect(firstUrl.origin).toBe("http://localhost:9000");
    expect(firstUrl.pathname).toBe(`/playground-documents/playground/${OWNER}/${DOCUMENT_ID}/pages/page-0011.webp`);
    expect(firstUrl.searchParams.get("X-Amz-Expires")).toBe("1800");
    expect(Date.parse(String(pageRange?.expiresAt)) - Date.now()).toBeGreaterThan(29 * 60 * 1000);
  });

  it("clamps the range to the document and the count to a sane batch", async () => {
    const lastPages = await getDocumentPages(standInPageSource(), OWNER, DOCUMENT_ID, 21, 10);
    const pastTheEnd = await getDocumentPages(standInPageSource(), OWNER, DOCUMENT_ID, 99, 10);
    const nonsense = await getDocumentPages(standInPageSource(), OWNER, DOCUMENT_ID, Number.NaN, Number.NaN);

    expect(lastPages?.pages.map((page) => page.index)).toEqual([21, 22, 23, 24, 25]);
    expect(pastTheEnd?.pages).toEqual([]);
    expect(nonsense?.pages.map((page) => page.index)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  });

  it.each([
    ["someone else", "11111111-2222-4333-8444-555555555555", DOCUMENT_ID],
    ["a browser with no user", undefined, DOCUMENT_ID],
    ["an ID that isn't a UUID", OWNER, "../../etc"],
  ])("gives %s nothing", async (_, ownerId, documentId) => {
    expect(await getDocumentPages(standInPageSource(), ownerId, documentId, 1, 10)).toBeNull();
  });
});
