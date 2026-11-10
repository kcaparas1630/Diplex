/** Next.js settings for the playground: a standalone server build, so the Docker image needs no node_modules. */
import type { NextConfig } from "next";

/** The playground's Next.js configuration. */
const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
