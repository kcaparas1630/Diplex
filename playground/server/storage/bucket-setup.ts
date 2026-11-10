/** Creates the playground's bucket on first start if it doesn't exist yet. */
import { CreateBucketCommand, HeadBucketCommand, type S3Client } from "@aws-sdk/client-s3";

/** Create the bucket unless it already exists; any other error (unreachable store, bad credentials) is thrown. */
export async function ensureBucketExists(serverClient: S3Client, bucketName: string): Promise<void> {
  try {
    await serverClient.send(new HeadBucketCommand({ Bucket: bucketName }));
  } catch (headError) {
    if (!isMissingBucket(headError)) {
      throw headError;
    }
    await serverClient.send(new CreateBucketCommand({ Bucket: bucketName }));
  }
}

/** Tell whether an S3 error says the bucket doesn't exist (a 404 from HeadBucket). */
function isMissingBucket(headError: unknown): boolean {
  const responseStatus = (headError as { $metadata?: { httpStatusCode?: number } }).$metadata?.httpStatusCode;
  const errorName = (headError as { name?: string }).name;
  return responseStatus === 404 || errorName === "NotFound" || errorName === "NoSuchBucket";
}
