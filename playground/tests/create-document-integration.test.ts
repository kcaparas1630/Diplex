/** Tests storing an upload on a real RustFS and Postgres, with a stand-in engine; skipped unless PLAYGROUND_TEST_* are set. */
import { ListObjectsV2Command } from "@aws-sdk/client-s3";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { ensureDocumentsTable } from "../server/database";
import { createDocument, type DocumentStore } from "../server/documents";
import { ensureBucketExists } from "../server/storage";
import { localServicesConfigured, openLocalServices } from "./local-services";

describe.skipIf(!localServicesConfigured)("createDocument on RustFS and Postgres", () => {
  const services = openLocalServices(`create-test-${Date.now()}`);
  const bucketName = services.settings.bucket.bucketName;
  /** The store, with a stand-in engine that returns two pages and a converted PDF. */
  const store: DocumentStore = {
    engine: { engineUrl: "http://unused", engineApiKey: undefined },
    serverClient: services.serverClient,
    signingClient: services.signingClient,
    bucketName,
    folderPrefix: "playground",
    database: services.database,
    render: async () => ({
      pageSizes: [{ index: 1, width: 612, height: 792 }, { index: 2, width: 792, height: 612 }],
      pageImages: [new Uint8Array([1]), new Uint8Array([2])],
      convertedPdf: new TextEncoder().encode("%PDF-1.7 converted"),
    }),
  };
  beforeAll(async () => {
    await ensureBucketExists(services.serverClient, bucketName);
    await ensureDocumentsTable(services.database);
  });
  afterAll(() => services.database.end());

  /** The keys stored under a folder. */
  async function storedKeys(folder: string): Promise<string[]> {
    const listing = await services.serverClient.send(new ListObjectsV2Command({ Bucket: bucketName, Prefix: `${folder}/` }));
    return (listing.Contents ?? []).map((stored) => String(stored.Key)).sort();
  }

  it("stores the files and one row holding the folder and page sizes", async () => {
    const documentRow = await createDocument(store, { ownerId: "user-1", fileName: "Thesis final (v2).docx", documentBytes: new Uint8Array([7]) });

    const storedRow = await services.database.query("SELECT folder, file_name, source_type, page_sizes FROM documents WHERE id = $1", [documentRow.id]);
    expect(storedRow.rows[0]).toEqual({
      folder: documentRow.folder,
      file_name: "Thesis final (v2).docx",
      source_type: "docx",
      page_sizes: [{ index: 1, width: 612, height: 792 }, { index: 2, width: 792, height: 612 }],
    });
    expect(await storedKeys(documentRow.folder)).toEqual([
      `${documentRow.folder}/document.pdf`,
      `${documentRow.folder}/original.docx`,
      `${documentRow.folder}/pages/page-0001.webp`,
      `${documentRow.folder}/pages/page-0002.webp`,
    ]);
  });

  it("leaves no files when the row can't be written", async () => {
    const failingStore: DocumentStore = { ...store, database: { query: async () => Promise.reject(new Error("row refused")) } };
    const ownerId = `user-${Date.now()}`;

    await expect(createDocument(failingStore, { ownerId, fileName: "a.docx", documentBytes: new Uint8Array([7]) })).rejects.toThrow("row refused");

    expect(await storedKeys(`playground/${ownerId}`)).toEqual([]);
  });
});
