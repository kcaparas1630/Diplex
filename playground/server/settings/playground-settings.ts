/** Reads the playground's settings from environment variables; storage and database credentials never leave the server. */

/** Where the bucket is and how to reach it: the server's endpoint, the one browsers reach, and the credentials. */
export interface BucketSettings {
  endpoint: string;
  publicEndpoint: string;
  region: string;
  accessKeyId: string;
  secretAccessKey: string;
  bucketName: string;
  folderPrefix: string;
}

/** Everything the playground's server needs: the engine, the database and the bucket. */
export interface PlaygroundSettings {
  engineUrl: string;
  engineApiKey: string | undefined;
  databaseUrl: string;
  bucket: BucketSettings;
}

/** The variables a process environment may hold, as Node gives them. */
export type EnvironmentVariables = Record<string, string | undefined>;

/** Read the settings from the environment, throwing an error that names any required variable that is missing. */
export function readPlaygroundSettings(environment: EnvironmentVariables): PlaygroundSettings {
  const endpoint = requireVariable(environment, "S3_ENDPOINT");
  return {
    engineUrl: requireVariable(environment, "DIPLEX_ENGINE_URL").replace(/\/+$/, ""),
    engineApiKey: environment.DIPLEX_API_KEY?.trim() || undefined,
    databaseUrl: requireVariable(environment, "DATABASE_URL"),
    bucket: {
      endpoint,
      publicEndpoint: environment.S3_PUBLIC_ENDPOINT?.trim() || endpoint,
      region: environment.S3_REGION?.trim() || "us-east-1",
      accessKeyId: requireVariable(environment, "S3_ACCESS_KEY_ID"),
      secretAccessKey: requireVariable(environment, "S3_SECRET_ACCESS_KEY"),
      bucketName: requireVariable(environment, "S3_BUCKET"),
      folderPrefix: (environment.S3_PREFIX?.trim() || "playground").replace(/^\/+|\/+$/g, ""),
    },
  };
}

/** Return a variable's trimmed value, or throw an error naming it when it is missing or empty. */
function requireVariable(environment: EnvironmentVariables, variableName: string): string {
  const configuredValue = environment[variableName]?.trim();
  if (!configuredValue) {
    throw new Error(`${variableName} is not set; see playground/README.md`);
  }
  return configuredValue;
}
