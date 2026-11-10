/** The playground's database: its Postgres pool, the documents table created on first start, and its rows. */
export { createDatabasePool } from "./database-pool";
export type { DatabaseQueries } from "./database-pool";
export { DOCUMENTS_TABLE_DEFINITION, ensureDocumentsTable } from "./documents-table";
export { insertDocumentRow, listDocumentRows, toDocumentRow } from "./document-rows";
export type { DocumentRow, NewDocumentRow, SqlQueries, StoredPageSize } from "./document-rows";
