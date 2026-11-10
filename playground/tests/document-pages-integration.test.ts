/** Tests that a signed page URL fetches the stored page from a real RustFS; skipped unless PLAYGROUND_TEST_* are set. */
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { ensureDocumentsTable } from "../server/database";
import { createDocument, getDocumentPages, type DocumentStore } from "../server/documents";
import { ensureBucketExists } from "../server/storage";
import { localServicesConfigured, openLocalServices } from "./local-services";

describe.skipIf(!localServicesConfigured)("signed page URLs on RustFS", () => {
  const services = openLocalServices(`pages-test-${Date.now()}`);
  /** The store, with a stand-in engine that returns one page. */
  const store: DocumentStore = {
    engine: { engineUrl: "http://unused", engineApiKey: undefined },
    serverClient: services.serverClient,
    signingClient: services.signingClient,
    bucketName: services.settings.bucket.bucketName,
    folderPrefix: "playground",
    database: services.database,
    render: async () => ({ pageSizes: [{ index: 1, width: 612, height: 792 }], pageImages: [new TextEncoder().encode("RIFF page one")], convertedPdf: undefined }),
  };
  beforeAll(async () => {
    await ensureBucketExists(services.serverClient, store.bucketName);
    await ensureDocumentsTable(services.database);
  });
  afterAll(() => services.database.end());

  it("returns a URL a browser can fetch the page image from, with its long cache header", async () => {
    const ownerId = crypto.randomUUID();
    const documentRow = await createDocument(store, { ownerId, fileName: "a.pdf", documentBytes: new TextEncoder().encode("%PDF-1.7") });

    const pageRange = await getDocumentPages(store, ownerId, documentRow.id, 1, 10);
    const pageResponse = await fetch(String(pageRange?.pages[0].url));

    expect(pageResponse.status).toBe(200);
    expect(await pageResponse.text()).toBe("RIFF page one");
    expect(pageResponse.headers.get("cache-control")).toBe("public, max-age=31536000, immutable");
  });
});
