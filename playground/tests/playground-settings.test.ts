/** Tests reading the playground's settings from environment variables. */
import { describe, expect, it } from "vitest";

import { readPlaygroundSettings } from "../server/settings";

/** A complete environment, as compose.yaml sets it. */
const completeEnvironment = {
  DIPLEX_ENGINE_URL: "http://engine:8000/",
  DIPLEX_API_KEY: "local-playground-engine-key",
  DATABASE_URL: "postgres://playground:playground@postgres:5432/playground",
  S3_ENDPOINT: "http://rustfs:9000",
  S3_PUBLIC_ENDPOINT: "http://localhost:9000",
  S3_REGION: "us-east-1",
  S3_ACCESS_KEY_ID: "playground",
  S3_SECRET_ACCESS_KEY: "playground-secret",
  S3_BUCKET: "playground-documents",
  S3_PREFIX: "/playground/",
};

describe("readPlaygroundSettings", () => {
  it("reads every setting, trimming the engine URL's slash and the prefix's slashes", () => {
    const settings = readPlaygroundSettings(completeEnvironment);

    expect(settings.engineUrl).toBe("http://engine:8000");
    expect(settings.engineApiKey).toBe("local-playground-engine-key");
    expect(settings.bucket).toEqual({
      endpoint: "http://rustfs:9000",
      publicEndpoint: "http://localhost:9000",
      region: "us-east-1",
      accessKeyId: "playground",
      secretAccessKey: "playground-secret",
      bucketName: "playground-documents",
      folderPrefix: "playground",
    });
  });

  it("falls back to the server endpoint for browsers, us-east-1 and the playground prefix, and no engine key", () => {
    const { S3_PUBLIC_ENDPOINT, S3_REGION, S3_PREFIX, DIPLEX_API_KEY, ...requiredOnly } = completeEnvironment;

    const settings = readPlaygroundSettings(requiredOnly);

    expect(settings.bucket.publicEndpoint).toBe("http://rustfs:9000");
    expect(settings.bucket.region).toBe("us-east-1");
    expect(settings.bucket.folderPrefix).toBe("playground");
    expect(settings.engineApiKey).toBeUndefined();
  });

  it.each(["DIPLEX_ENGINE_URL", "DATABASE_URL", "S3_ENDPOINT", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET"])(
    "refuses to start without %s, naming it",
    (variableName) => {
      expect(() => readPlaygroundSettings({ ...completeEnvironment, [variableName]: " " })).toThrow(variableName);
    },
  );
});
