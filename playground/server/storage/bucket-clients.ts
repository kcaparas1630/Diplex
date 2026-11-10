/** Builds the S3 clients: one for the server's own calls, one that signs URLs with the endpoint browsers reach. */
import { S3Client } from "@aws-sdk/client-s3";

import type { BucketSettings } from "../settings";

/** The two S3 clients the playground uses; both hold the credentials, and neither ever reaches a browser. */
export interface BucketClients {
  serverClient: S3Client;
  signingClient: S3Client;
}

/** Create both clients, with path-style URLs, which local S3-compatible stores such as RustFS expect. */
export function createBucketClients(bucketSettings: BucketSettings): BucketClients {
  const credentials = { accessKeyId: bucketSettings.accessKeyId, secretAccessKey: bucketSettings.secretAccessKey };
  return {
    serverClient: new S3Client({ endpoint: bucketSettings.endpoint, region: bucketSettings.region, credentials, forcePathStyle: true }),
    // A presigned URL is signed for its host, so it must name the endpoint the browser will fetch from.
    signingClient: new S3Client({ endpoint: bucketSettings.publicEndpoint, region: bucketSettings.region, credentials, forcePathStyle: true }),
  };
}
