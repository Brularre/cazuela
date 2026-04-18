import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      { source: "/api/dashboard/:path*", destination: `${backend}/dashboard/:path*` },
      { source: "/api/auth/:path*", destination: `${backend}/auth/:path*` },
    ];
  },
};

export default nextConfig;
