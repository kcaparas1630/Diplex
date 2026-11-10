/** Deletes a document the way ADR 001 §5 says: set its row's deletion time, then remove its folder from the bucket. */
import type { S3Client } from "@aws-sdk/client-s3";

import { markDocumentDeleted, type SqlQueries } from "../database";
import { removeDocumentFolder } from "../storage";

/** What deleting a document needs: the database and the bucket. */
export interface DeletionTarget {
  database: SqlQueries;
  serverClient: S3Client;
  bucketName: string;
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** Delete the owner's document and its files; return false when there is nothing of theirs to delete. */
export async function deleteDocument(target: DeletionTarget, ownerId: string | undefined, documentId: string): Promise<boolean> {
  if (!ownerId || !UUID_PATTERN.test(documentId)) {
    return false;
  }
  // The row goes first, so the document vanishes from the app at once even if removing the files is slow or fails;
  // its deletion time and folder stay, so a cleanup can finish the files later.
  const folder = await markDocumentDeleted(target.database, documentId, ownerId);
  if (!folder) {
    return false;
  }
  await removeDocumentFolder(target.serverClient, target.bucketName, folder);
  return true;
}
