/** Reads and writes rows of the documents table: one per document, holding its folder and page sizes, never a URL. */

/** A page's size in points, as stored from the engine's manifest. */
export interface StoredPageSize {
  index: number;
  width: number;
  height: number;
}

/** One document as the database keeps it. */
export interface DocumentRow {
  id: string;
  ownerId: string;
  fileName: string;
  folder: string;
  sourceType: "docx" | "pdf";
  pageSizes: StoredPageSize[];
  createdAt: Date;
  deletedAt: Date | null;
}

/** What a new row needs; the database fills in its creation time. */
export type NewDocumentRow = Omit<DocumentRow, "createdAt" | "deletedAt">;

/** Anything that runs parameterised SQL, such as a pg Pool. */
export interface SqlQueries {
  query(queryText: string, queryValues?: unknown[]): Promise<{ rows: Record<string, unknown>[] }>;
}

/** Insert a new document's row and return it as stored. */
export async function insertDocumentRow(database: SqlQueries, newRow: NewDocumentRow): Promise<DocumentRow> {
  const inserted = await database.query(
    `INSERT INTO documents (id, owner_id, file_name, folder, source_type, page_sizes)
     VALUES ($1, $2, $3, $4, $5, $6)
     RETURNING id, owner_id, file_name, folder, source_type, page_sizes, created_at, deleted_at`,
    [newRow.id, newRow.ownerId, newRow.fileName, newRow.folder, newRow.sourceType, JSON.stringify(newRow.pageSizes)],
  );
  return toDocumentRow(inserted.rows[0]);
}

/** The owner's documents that aren't deleted, newest first. */
export async function listDocumentRows(database: SqlQueries, ownerId: string): Promise<DocumentRow[]> {
  const listed = await database.query(
    `SELECT id, owner_id, file_name, folder, source_type, page_sizes, created_at, deleted_at
     FROM documents WHERE owner_id = $1 AND deleted_at IS NULL ORDER BY created_at DESC`,
    [ownerId],
  );
  return listed.rows.map(toDocumentRow);
}

/** The owner's document with this ID, or null when it doesn't exist, is deleted, or belongs to someone else. */
export async function findOwnedDocumentRow(database: SqlQueries, documentId: string, ownerId: string): Promise<DocumentRow | null> {
  const found = await database.query(
    `SELECT id, owner_id, file_name, folder, source_type, page_sizes, created_at, deleted_at
     FROM documents WHERE id = $1 AND owner_id = $2 AND deleted_at IS NULL`,
    [documentId, ownerId],
  );
  return found.rows.length === 1 ? toDocumentRow(found.rows[0]) : null;
}

/** Turn a database row's columns into a DocumentRow. */
export function toDocumentRow(columns: Record<string, unknown>): DocumentRow {
  return {
    id: String(columns.id),
    ownerId: String(columns.owner_id),
    fileName: String(columns.file_name),
    folder: String(columns.folder),
    sourceType: columns.source_type as DocumentRow["sourceType"],
    pageSizes: columns.page_sizes as StoredPageSize[],
    createdAt: new Date(columns.created_at as string | Date),
    deletedAt: columns.deleted_at ? new Date(columns.deleted_at as string | Date) : null,
  };
}
