/** The real RustFS and Postgres the integration tests use when PLAYGROUND_TEST_* variables point at them (CI starts both). */
import { createDatabasePool } from "../server/database";
import { readPlaygroundSettings, type PlaygroundSettings } from "../server/settings";
import { createBucketClients } from "../server/storage";

/** Whether the integration tests have a store and a database to run against. */
export const localServicesConfigured = Boolean(process.env.PLAYGROUND_TEST_DATABASE_URL && process.env.PLAYGROUND_TEST_S3_ENDPOINT);

/** Settings for the local services, with a bucket name of the test's own so tests don't share state. */
export function localServiceSettings(bucketName: string): PlaygroundSettings {
  return readPlaygroundSettings({
    DIPLEX_ENGINE_URL: process.env.PLAYGROUND_TEST_ENGINE_URL ?? "http://127.0.0.1:8000",
    DATABASE_URL: process.env.PLAYGROUND_TEST_DATABASE_URL,
    S3_ENDPOINT: process.env.PLAYGROUND_TEST_S3_ENDPOINT,
    S3_ACCESS_KEY_ID: process.env.PLAYGROUND_TEST_S3_ACCESS_KEY_ID ?? "playground",
    S3_SECRET_ACCESS_KEY: process.env.PLAYGROUND_TEST_S3_SECRET_ACCESS_KEY ?? "playground-secret",
    S3_BUCKET: bucketName,
  });
}

/** Open real clients on the local services. */
export function openLocalServices(bucketName: string) {
  const settings = localServiceSettings(bucketName);
  return { settings, ...createBucketClients(settings.bucket), database: createDatabasePool(settings.databaseUrl) };
}
