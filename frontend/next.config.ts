import type { NextConfig } from "next";

// Static export: single origin, no CORS, served by FastAPI as static files.
// See planning/PLAN.md Section 3 (Single Container, Single Port).
const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true, // Next Image Optimization needs a server; static export has none
  },
};

export default nextConfig;
