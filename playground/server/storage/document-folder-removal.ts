/** Removes a document's whole folder from the bucket: every object under {prefix}/{userId}/{documentId}/. */
import { DeleteObjectsCommand, ListObjectsV2Command, type S3Client } from "@aws-sdk/client-s3";

/** Delete every object under the folder, a page of keys (up to 1,000) at a time, and return how many were deleted. */
export async function removeDocumentFolder(client: S3Client, bucketName: string, folder: string): Promise<number> {
  let removedCount = 0;
  let continuationToken: string | undefined;
  do {
    const listing = await client.send(
      new ListObjectsV2Command({ Bucket: bucketName, Prefix: `${folder}/`, ContinuationToken: continuationToken }),
    );
    const keys = (listing.Contents ?? []).flatMap((stored) => (stored.Key ? [{ Key: stored.Key }] : []));
    if (keys.length > 0) {
      await client.send(new DeleteObjectsCommand({ Bucket: bucketName, Delete: { Objects: keys, Quiet: true } }));
      removedCount += keys.length;
    }
    continuationToken = listing.IsTruncated ? listing.NextContinuationToken : undefined;
  } while (continuationToken);
  return removedCount;
}
