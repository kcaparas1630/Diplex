/** Tests deleting a stored document on a real RustFS and Postgres; skipped unless PLAYGROUND_TEST_* are set. */
import { ListObjectsV2Command } from "@aws-sdk/client-s3";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { ensureDocumentsTable } from "../server/database";
import { createDocument, deleteDocument, listDocuments, type DocumentStore } from "../server/documents";
import { ensureBucketExists } from "../server/storage";
import { localServicesConfigured, openLocalServices } from "./local-services";

describe.skipIf(!localServicesConfigured)("deleteDocument on RustFS and Postgres", () => {
  const services = openLocalServices(`delete-test-${Date.now()}`);
  /** The store, with a stand-in engine that returns two pages. */
  const store: DocumentStore = {
    engine: { engineUrl: "http://unused", engineApiKey: undefined },
    serverClient: services.serverClient,
    signingClient: services.signingClient,
    bucketName: services.settings.bucket.bucketName,
    folderPrefix: "playground",
    database: services.database,
    render: async () => ({ pageSizes: [{ index: 1, width: 1, height: 1 }, { index: 2, width: 1, height: 1 }], pageImages: [new Uint8Array([1]), new Uint8Array([2])], convertedPdf: undefined }),
  };
  beforeAll(async () => {
    await ensureBucketExists(services.serverClient, store.bucketName);
    await ensureDocumentsTable(services.database);
  });
  afterAll(() => services.database.end());

  it("removes every file, keeps the row with its deletion time, and drops it from the list", async () => {
    const ownerId = crypto.randomUUID();
    const documentRow = await createDocument(store, { ownerId, fileName: "a.pdf", documentBytes: new TextEncoder().encode("%PDF") });

    expect(await deleteDocument(store, ownerId, documentRow.id)).toBe(true);

    const remaining = await services.serverClient.send(new ListObjectsV2Command({ Bucket: store.bucketName, Prefix: `${documentRow.folder}/` }));
    expect(remaining.KeyCount ?? 0).toBe(0);
    const storedRow = await services.database.query("SELECT deleted_at FROM documents WHERE id = $1", [documentRow.id]);
    expect(storedRow.rows[0].deleted_at).toBeInstanceOf(Date);
    expect(await listDocuments(services.database, ownerId)).toEqual([]);
  });
});
