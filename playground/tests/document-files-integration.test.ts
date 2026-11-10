/** Tests writing a document's files to a real RustFS; skipped unless PLAYGROUND_TEST_* variables are set. */
import { HeadObjectCommand, ListObjectsV2Command } from "@aws-sdk/client-s3";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { documentKeys, ensureBucketExists, uploadDocumentFiles } from "../server/storage";
import { localServicesConfigured, openLocalServices } from "./local-services";

describe.skipIf(!localServicesConfigured)("document files on RustFS", () => {
  const services = openLocalServices(`files-test-${Date.now()}`);
  const bucketName = services.settings.bucket.bucketName;
  beforeAll(() => ensureBucketExists(services.serverClient, bucketName));
  afterAll(() => services.database.end());

  it("stores a PDF upload, its copy as document.pdf and its pages, with the page cache headers", async () => {
    await uploadDocumentFiles(services.serverClient, bucketName, "playground/user-1/doc-1", {
      originalBytes: new TextEncoder().encode("%PDF-1.7 original"),
      sourceType: "pdf",
      convertedPdf: undefined,
      pageImages: [new Uint8Array([1, 2, 3]), new Uint8Array([4, 5, 6])],
    });

    const listing = await services.serverClient.send(new ListObjectsV2Command({ Bucket: bucketName, Prefix: "playground/user-1/doc-1/" }));
    expect(listing.Contents?.map((stored) => stored.Key).sort()).toEqual([
      "playground/user-1/doc-1/document.pdf",
      "playground/user-1/doc-1/original.pdf",
      "playground/user-1/doc-1/pages/page-0001.webp",
      "playground/user-1/doc-1/pages/page-0002.webp",
    ]);
    const firstPage = await services.serverClient.send(new HeadObjectCommand({ Bucket: bucketName, Key: documentKeys.page("playground/user-1/doc-1", 1) }));
    expect([firstPage.ContentType, firstPage.CacheControl]).toEqual(["image/webp", "public, max-age=31536000, immutable"]);
    const copiedPdf = await services.serverClient.send(new HeadObjectCommand({ Bucket: bucketName, Key: "playground/user-1/doc-1/document.pdf" }));
    expect(copiedPdf.ContentLength).toBe("%PDF-1.7 original".length);
  });
});
