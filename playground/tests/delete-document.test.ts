/** Tests deleting a document with stand-ins: the row is marked first, then the folder goes; nothing for others. */
import type { S3Client } from "@aws-sdk/client-s3";
import { describe, expect, it } from "vitest";

import { deleteDocument, type DeletionTarget } from "../server/documents";

const OWNER = "0b5c2f7e-8a1d-4c3e-9f20-6d1a2b3c4d5e";
const DOCUMENT_ID = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d";

/** A target whose database marks OWNER's document once, and whose bucket records what it is asked to do. */
function standInTarget() {
  const steps: string[] = [];
  let alreadyDeleted = false;
  const target: DeletionTarget = {
    database: {
      query: async (queryText: string, queryValues?: unknown[]) => {
        steps.push(queryText.split(" ")[0]);
        if (queryValues?.[1] !== OWNER || alreadyDeleted) {
          return { rows: [] };
        }
        alreadyDeleted = true;
        return { rows: [{ folder: `playground/${OWNER}/${DOCUMENT_ID}` }] };
      },
    },
    serverClient: {
      send: async (command: { constructor: { name: string }; input: { Prefix?: string } }) => {
        steps.push(`${command.constructor.name} ${command.input.Prefix ?? ""}`.trim());
        return command.constructor.name === "ListObjectsV2Command" ? { Contents: [{ Key: "k" }], IsTruncated: false } : {};
      },
    } as unknown as S3Client,
    bucketName: "bucket",
  };
  return { target, steps };
}

describe("deleteDocument", () => {
  it("marks the row deleted, then removes the document's whole folder", async () => {
    const { target, steps } = standInTarget();

    expect(await deleteDocument(target, OWNER, DOCUMENT_ID)).toBe(true);

    expect(steps).toEqual(["UPDATE", `ListObjectsV2Command playground/${OWNER}/${DOCUMENT_ID}/`, "DeleteObjectsCommand"]);
  });

  it("does nothing the second time, or for anyone but the owner", async () => {
    const { target, steps } = standInTarget();
    await deleteDocument(target, OWNER, DOCUMENT_ID);
    steps.length = 0;

    expect(await deleteDocument(target, OWNER, DOCUMENT_ID)).toBe(false);
    expect(await deleteDocument(target, "11111111-2222-4333-8444-555555555555", DOCUMENT_ID)).toBe(false);
    expect(await deleteDocument(target, undefined, DOCUMENT_ID)).toBe(false);
    expect(steps.filter((step) => step !== "UPDATE")).toEqual([]);
  });
});
