/** Builds the playground's server-side services once per process, from its settings, and prepares storage on first start. */
import type { S3Client } from "@aws-sdk/client-s3";
import type { Pool } from "pg";

import { createDatabasePool, ensureDocumentsTable } from "./database";
import { readPlaygroundSettings, type PlaygroundSettings } from "./settings";
import { createBucketClients, ensureBucketExists } from "./storage";

/** The settings and clients every server route shares. */
export interface PlaygroundServices {
  settings: PlaygroundSettings;
  serverClient: S3Client;
  signingClient: S3Client;
  database: Pool;
}

const STARTUP_ATTEMPTS = 30;
const STARTUP_RETRY_MILLISECONDS = 1000;

let sharedServices: PlaygroundServices | undefined;

/** Return the process's services, building them from the environment the first time. */
export function getPlaygroundServices(): PlaygroundServices {
  if (!sharedServices) {
    const settings = readPlaygroundSettings(process.env);
    sharedServices = { settings, ...createBucketClients(settings.bucket), database: createDatabasePool(settings.databaseUrl) };
  }
  return sharedServices;
}

/** Create the bucket and the documents table if they don't exist, retrying while the store or database starts. */
export async function prepareStorage(): Promise<void> {
  const services = getPlaygroundServices();
  for (let attempt = 1; ; attempt += 1) {
    try {
      await ensureBucketExists(services.serverClient, services.settings.bucket.bucketName);
      await ensureDocumentsTable(services.database);
      return;
    } catch (startupError) {
      if (attempt >= STARTUP_ATTEMPTS) {
        throw startupError;
      }
      await new Promise((resolve) => setTimeout(resolve, STARTUP_RETRY_MILLISECONDS));
    }
  }
}
