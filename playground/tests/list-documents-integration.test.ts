/** Tests listing a user's documents on a real Postgres; skipped unless PLAYGROUND_TEST_* variables are set. */
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { ensureDocumentsTable, insertDocumentRow } from "../server/database";
import { listDocuments } from "../server/documents";
import { localServicesConfigured, openLocalServices } from "./local-services";

describe.skipIf(!localServicesConfigured)("listDocuments on Postgres", () => {
  const services = openLocalServices("unused-bucket");
  const ownerId = `list-owner-${Date.now()}`;
  beforeAll(() => ensureDocumentsTable(services.database));
  afterAll(() => services.database.end());

  it("lists only the owner's documents that aren't deleted, newest first, with their page counts", async () => {
    const pageSizes = [{ index: 1, width: 612, height: 792 }, { index: 2, width: 612, height: 792 }];
    for (const fileName of ["first.pdf", "second.docx", "deleted.pdf"]) {
      await insertDocumentRow(services.database, { id: crypto.randomUUID(), ownerId, fileName, folder: "f", sourceType: fileName.endsWith("docx") ? "docx" : "pdf", pageSizes });
    }
    await insertDocumentRow(services.database, { id: crypto.randomUUID(), ownerId: "someone-else", fileName: "theirs.pdf", folder: "f", sourceType: "pdf", pageSizes });
    await services.database.query("UPDATE documents SET deleted_at = now() WHERE owner_id = $1 AND file_name = 'deleted.pdf'", [ownerId]);

    const listedDocuments = await listDocuments(services.database, ownerId);

    expect(listedDocuments.map((listed) => [listed.fileName, listed.sourceType, listed.pageCount])).toEqual([
      ["second.docx", "docx", 2],
      ["first.pdf", "pdf", 2],
    ]);
  });
});
