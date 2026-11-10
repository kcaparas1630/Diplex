/** The playground's database: its Postgres pool, and the documents table created on first start. */
export { createDatabasePool } from "./database-pool";
export type { DatabaseQueries } from "./database-pool";
export { DOCUMENTS_TABLE_DEFINITION, ensureDocumentsTable } from "./documents-table";
