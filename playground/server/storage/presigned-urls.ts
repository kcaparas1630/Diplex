/** Signs short-lived GET URLs for a document's files, on demand; the playground never stores a signed URL (ADR 001 §5). */
import { GetObjectCommand, type S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

/** How long a signed URL works: within ADR 001 §5's 15 to 60 minutes, so a viewer can reuse it while the user reads. */
export const SIGNED_URL_SECONDS = 30 * 60;

/** Sign a GET URL for one key, optionally telling the browser to download it under a file name. */
export async function signGetUrl(
  signingClient: S3Client,
  bucketName: string,
  objectKey: string,
  downloadDisposition?: string,
): Promise<string> {
  const getCommand = new GetObjectCommand({ Bucket: bucketName, Key: objectKey, ResponseContentDisposition: downloadDisposition });
  return getSignedUrl(signingClient, getCommand, { expiresIn: SIGNED_URL_SECONDS });
}
