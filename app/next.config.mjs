/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  typedRoutes: true,
  serverExternalPackages: [
    "rehype-mermaid",
    "mermaid-isomorphic",
    "playwright",
    "playwright-core",
  ],
};

export default nextConfig;
