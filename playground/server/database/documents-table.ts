/** Creates the documents table on first start: one row per document, as ADR 001 §5 describes. */

/** The table's definition. It stores the folder, never a presigned URL; a deleted document keeps its row with a deletion time. */
export const DOCUMENTS_TABLE_DEFINITION = `
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY,
  owner_id text NOT NULL,
  file_name text NOT NULL,
  folder text NOT NULL,
  source_type text NOT NULL CHECK (source_type IN ('docx', 'pdf')),
  page_sizes jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz
);
CREATE INDEX IF NOT EXISTS documents_by_owner ON documents (owner_id, created_at DESC) WHERE deleted_at IS NULL;
`;

/** Anything that runs SQL, such as a pg Pool. */
interface SqlRunner {
  query(queryText: string): Promise<unknown>;
}

/** Create the table and its index unless they exist. */
export async function ensureDocumentsTable(database: SqlRunner): Promise<void> {
  await database.query(DOCUMENTS_TABLE_DEFINITION);
}
