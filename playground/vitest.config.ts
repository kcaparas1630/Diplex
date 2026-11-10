/** Vitest settings for the playground: the unit tests live in tests/ and run in Node. */
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
  },
});
