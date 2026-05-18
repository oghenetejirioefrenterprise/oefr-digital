/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingIncludes: {
    "/**/*": ["../state/products/**/*.json"]
  }
};

export default nextConfig;
