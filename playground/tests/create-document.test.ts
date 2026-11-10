/** Tests storing an upload with stand-ins for the engine, the bucket and the database: success, and cleanup on failure. */
import type { S3Client } from "@aws-sdk/client-s3";
import { describe, expect, it } from "vitest";

import { createDocument, type DocumentStore } from "../server/documents";
import type { RenderResult } from "../server/engine-client";

const RENDERED_DOCX: RenderResult = {
  pageSizes: [{ index: 1, width: 595.28, height: 841.89 }],
  pageImages: [new Uint8Array([1])],
  convertedPdf: new Uint8Array([2]),
};

/** A store whose bucket records commands, whose database records inserts or fails, and whose engine returns a result. */
function standInStore(options: { rowFails?: boolean; uploadFails?: boolean; renderResult?: RenderResult }) {
  const bucketCommands: string[] = [];
  const insertedValues: unknown[][] = [];
  const serverClient = {
    send: async (command: { constructor: { name: string }; input: { Key?: string; Prefix?: string } }) => {
      bucketCommands.push(`${command.constructor.name} ${command.input.Key ?? command.input.Prefix ?? ""}`);
      if (options.uploadFails && command.constructor.name === "PutObjectCommand" && command.input.Key?.includes("/pages/")) {
        throw new Error("the bucket went away");
      }
      if (command.constructor.name === "ListObjectsV2Command") {
        return { Contents: [{ Key: `${command.input.Prefix}original.docx` }], IsTruncated: false };
      }
      return {};
    },
  } as unknown as S3Client;
  const store: DocumentStore = {
    engine: { engineUrl: "http://engine:8000", engineApiKey: undefined },
    serverClient,
    signingClient: serverClient,
    bucketName: "bucket",
    folderPrefix: "playground",
    database: {
      query: async (queryText: string, queryValues?: unknown[]) => {
        if (options.rowFails) {
          throw new Error("the database refused the row");
        }
        insertedValues.push(queryValues ?? []);
        return { rows: [{ id: queryValues?.[0], owner_id: queryValues?.[1], file_name: queryValues?.[2], folder: queryValues?.[3], source_type: queryValues?.[4], page_sizes: JSON.parse(String(queryValues?.[5])), created_at: new Date(), deleted_at: null }] };
      },
    },
    render: async () => options.renderResult ?? RENDERED_DOCX,
  };
  return { store, bucketCommands, insertedValues };
}

const UPLOAD = { ownerId: "user-1", fileName: "thesis.docx", documentBytes: new Uint8Array([9]) };

describe("createDocument", () => {
  it("uploads the files, then writes one row with the folder and the page sizes, never a URL", async () => {
    const { store, bucketCommands, insertedValues } = standInStore({});

    const documentRow = await createDocument(store, UPLOAD);

    expect(documentRow.folder).toBe(`playground/user-1/${documentRow.id}`);
    expect(documentRow).toMatchObject({ ownerId: "user-1", fileName: "thesis.docx", sourceType: "docx", pageSizes: RENDERED_DOCX.pageSizes });
    expect(bucketCommands).toEqual([
      `PutObjectCommand ${documentRow.folder}/original.docx`,
      `PutObjectCommand ${documentRow.folder}/document.pdf`,
      `PutObjectCommand ${documentRow.folder}/pages/page-0001.webp`,
    ]);
    expect(insertedValues).toHaveLength(1);
    expect(JSON.stringify(insertedValues)).not.toMatch(/https?:/);
  });

  it("treats an upload that came back without a PDF as a PDF", async () => {
    const { store } = standInStore({ renderResult: { ...RENDERED_DOCX, convertedPdf: undefined } });

    expect((await createDocument(store, { ...UPLOAD, fileName: "scan.pdf" })).sourceType).toBe("pdf");
  });

  it("removes the uploaded files when the row write fails, and passes the error on", async () => {
    const { store, bucketCommands } = standInStore({ rowFails: true });

    await expect(createDocument(store, UPLOAD)).rejects.toThrow("the database refused the row");

    expect(bucketCommands.at(-2)).toMatch(/^ListObjectsV2Command playground\/user-1\/[\w-]+\/$/);
    expect(bucketCommands.at(-1)).toMatch(/^DeleteObjectsCommand/);
  });

  it("removes what was uploaded when an upload fails part way, and writes no row", async () => {
    const { store, bucketCommands, insertedValues } = standInStore({ uploadFails: true });

    await expect(createDocument(store, UPLOAD)).rejects.toThrow("the bucket went away");

    expect(insertedValues).toEqual([]);
    expect(bucketCommands.some((command) => command.startsWith("DeleteObjectsCommand"))).toBe(true);
  });
});
