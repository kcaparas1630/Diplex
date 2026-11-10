/** Reads one of the current user's documents for its page: name, type and page sizes; nothing for anyone else. */
import { findOwnedDocumentRow, type SqlQueries, type StoredPageSize } from "../database";

/** A document as its page shows it. */
export interface OwnedDocument {
  id: string;
  fileName: string;
  sourceType: "docx" | "pdf";
  pageSizes: StoredPageSize[];
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** The owner's document, or null when there is no owner, the ID is malformed, or the document isn't theirs. */
export async function getOwnedDocument(database: SqlQueries, ownerId: string | undefined, documentId: string): Promise<OwnedDocument | null> {
  if (!ownerId || !UUID_PATTERN.test(documentId)) {
    return null;
  }
  const documentRow = await findOwnedDocumentRow(database, documentId, ownerId);
  return documentRow
    ? { id: documentRow.id, fileName: documentRow.fileName, sourceType: documentRow.sourceType, pageSizes: documentRow.pageSizes }
    : null;
}
