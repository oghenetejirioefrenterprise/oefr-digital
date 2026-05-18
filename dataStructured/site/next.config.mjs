import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Tell Next.js the monorepo root is one level up so it traces state/products
  // and uploads at Vercel match local-dev behavior.
  outputFileTracingRoot: path.join(__dirname, ".."),
  outputFileTracingIncludes: {
    "/**/*": ["../state/products/**/*.json"]
  }
};

export default nextConfig;
