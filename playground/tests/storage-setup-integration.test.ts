/** Tests first-start setup against a real RustFS and Postgres; skipped unless PLAYGROUND_TEST_* variables are set. */
import { HeadBucketCommand } from "@aws-sdk/client-s3";
import { afterAll, describe, expect, it } from "vitest";

import { ensureDocumentsTable } from "../server/database";
import { ensureBucketExists } from "../server/storage";
import { localServicesConfigured, openLocalServices } from "./local-services";

describe.skipIf(!localServicesConfigured)("first-start setup on RustFS and Postgres", () => {
  const services = openLocalServices(`setup-test-${Date.now()}`);
  afterAll(() => services.database.end());

  it("creates the bucket, and a second start finds it", async () => {
    await ensureBucketExists(services.serverClient, services.settings.bucket.bucketName);
    await ensureBucketExists(services.serverClient, services.settings.bucket.bucketName);

    await expect(services.serverClient.send(new HeadBucketCommand({ Bucket: services.settings.bucket.bucketName }))).resolves.toBeDefined();
  });

  it("creates the documents table, and a second start leaves it", async () => {
    await ensureDocumentsTable(services.database);
    await ensureDocumentsTable(services.database);

    const columns = await services.database.query(
      "SELECT column_name FROM information_schema.columns WHERE table_name = 'documents' ORDER BY ordinal_position",
    );
    expect(columns.rows.map((column) => column.column_name)).toEqual([
      "id", "owner_id", "file_name", "folder", "source_type", "page_sizes", "created_at", "deleted_at",
    ]);
  });
});
