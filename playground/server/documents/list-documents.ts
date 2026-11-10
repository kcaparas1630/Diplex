/** Lists a user's documents for the home page, newest first, without anything the browser shouldn't see. */
import { listDocumentRows, type SqlQueries } from "../database";

/** A document as the home page lists it. */
export interface ListedDocument {
  id: string;
  fileName: string;
  sourceType: "docx" | "pdf";
  pageCount: number;
  createdAt: string;
}

/** The owner's documents that aren't deleted, newest first. */
export async function listDocuments(database: SqlQueries, ownerId: string): Promise<ListedDocument[]> {
  const documentRows = await listDocumentRows(database, ownerId);
  return documentRows.map((documentRow) => ({
    id: documentRow.id,
    fileName: documentRow.fileName,
    sourceType: documentRow.sourceType,
    pageCount: documentRow.pageSizes.length,
    createdAt: documentRow.createdAt.toISOString(),
  }));
}
