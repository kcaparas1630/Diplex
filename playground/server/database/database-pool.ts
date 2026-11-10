/** Opens the playground's Postgres connection pool from DATABASE_URL. */
import { Pool } from "pg";

/** The database calls the playground makes; a pg Pool provides them, and tests stand in for it. */
export interface DatabaseQueries {
  query(queryText: string, queryValues?: unknown[]): Promise<{ rows: Record<string, unknown>[]; rowCount: number | null }>;
}

/** Open a small pool; the playground serves one person at a time. */
export function createDatabasePool(databaseUrl: string): Pool {
  return new Pool({ connectionString: databaseUrl, max: 5 });
}
