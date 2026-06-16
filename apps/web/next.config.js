/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["@ribcage/shared-types"],
};

module.exports = nextConfig;
