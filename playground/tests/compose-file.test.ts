/** Tests playground/compose.yaml: the engine has no network but its own internal one, and only the playground reaches it. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";

/** The compose file, parsed. */
const composeFile = parse(readFileSync(join(__dirname, "..", "compose.yaml"), "utf8"));

describe("compose.yaml", () => {
  it("puts the engine on an internal network only, so it has no egress (ADR 013)", () => {
    expect(composeFile.services.engine.networks).toEqual(["engine-only"]);
    expect(composeFile.networks["engine-only"].internal).toBe(true);
    expect(composeFile.services.engine.ports).toBeUndefined();
  });

  it("lets only the playground reach the engine", () => {
    const servicesOnEngineNetwork = Object.entries<{ networks?: string[] }>(composeFile.services)
      .filter(([, service]) => service.networks?.includes("engine-only"))
      .map(([serviceName]) => serviceName);
    expect(servicesOnEngineNetwork.sort()).toEqual(["engine", "playground"]);
  });

  it("builds the engine from the repository's root Dockerfile", () => {
    expect(composeFile.services.engine.build).toBe("..");
  });

  it("publishes ports on this machine's loopback only", () => {
    const publishedPorts = Object.values<{ ports?: string[] }>(composeFile.services).flatMap((service) => service.ports ?? []);
    expect(publishedPorts.length).toBeGreaterThan(0);
    for (const publishedPort of publishedPorts) {
      expect(publishedPort.startsWith("127.0.0.1:")).toBe(true);
    }
  });
});
