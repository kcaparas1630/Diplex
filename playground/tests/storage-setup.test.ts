/** Tests creating the bucket and the documents table on first start, with stand-in S3 and database clients. */
import { CreateBucketCommand, HeadBucketCommand, type S3Client } from "@aws-sdk/client-s3";
import { describe, expect, it } from "vitest";

import { DOCUMENTS_TABLE_DEFINITION, ensureDocumentsTable } from "../server/database";
import { ensureBucketExists } from "../server/storage";

/** A stand-in S3 client that records each command and answers HeadBucket as the test sets. */
function standInS3Client(headBucketError: unknown): { client: S3Client; sentCommands: string[] } {
  const sentCommands: string[] = [];
  const client = {
    send: async (command: unknown) => {
      sentCommands.push((command as object).constructor.name);
      if (command instanceof HeadBucketCommand && headBucketError) {
        throw headBucketError;
      }
      return {};
    },
  } as unknown as S3Client;
  return { client, sentCommands };
}

describe("ensureBucketExists", () => {
  it("leaves an existing bucket alone", async () => {
    const { client, sentCommands } = standInS3Client(undefined);

    await ensureBucketExists(client, "playground-documents");

    expect(sentCommands).toEqual(["HeadBucketCommand"]);
  });

  it("creates the bucket when HeadBucket says it is missing", async () => {
    const { client, sentCommands } = standInS3Client({ name: "NotFound", $metadata: { httpStatusCode: 404 } });

    await ensureBucketExists(client, "playground-documents");

    expect(sentCommands).toEqual(["HeadBucketCommand", "CreateBucketCommand"]);
    expect(new CreateBucketCommand({ Bucket: "x" })).toBeInstanceOf(CreateBucketCommand);
  });

  it("passes on any other error, such as bad credentials", async () => {
    const forbidden = { name: "Forbidden", $metadata: { httpStatusCode: 403 } };
    const { client } = standInS3Client(forbidden);

    await expect(ensureBucketExists(client, "playground-documents")).rejects.toBe(forbidden);
  });
});

describe("ensureDocumentsTable", () => {
  it("creates the table and its index only if they don't exist", async () => {
    const queries: string[] = [];

    await ensureDocumentsTable({ query: async (queryText: string) => queries.push(queryText) });

    expect(queries).toEqual([DOCUMENTS_TABLE_DEFINITION]);
    expect(DOCUMENTS_TABLE_DEFINITION).toContain("CREATE TABLE IF NOT EXISTS documents");
    expect(DOCUMENTS_TABLE_DEFINITION).toContain("CREATE INDEX IF NOT EXISTS");
    expect(DOCUMENTS_TABLE_DEFINITION).not.toMatch(/url/i);
  });
});
