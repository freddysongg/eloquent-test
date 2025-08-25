/** @type {import('next').NextConfig} */
const nextConfig = {
  // React strict mode for better development experience
  reactStrictMode: true,

  // Enable SWC minifier for better performance
  swcMinify: true,

  // Image optimization configuration
  images: {
    domains: [
      "images.clerk.dev", // Clerk profile images
      "img.clerk.com", // Clerk profile images
      "via.placeholder.com", // Placeholder images
    ],
    formats: ["image/webp", "image/avif"],
  },

  // Environment variables available in the browser
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || "Eloquent AI",
    NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION || "0.1.0",
  },

  // Experimental features
  experimental: {
    // App router optimizations
    optimizePackageImports: ["lucide-react", "@radix-ui/react-icons"],

    // Server components optimizations
    serverComponentsExternalPackages: [],
  },

  // Webpack configuration
  webpack: (config, { dev, isServer }) => {
    // Optimize bundle in production
    if (!dev && !isServer) {
      config.optimization.splitChunks.chunks = "all";
      config.optimization.splitChunks.cacheGroups = {
        ...config.optimization.splitChunks.cacheGroups,
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: "vendors",
          chunks: "all",
          priority: 10,
        },
        ui: {
          test: /[\\/]node_modules[\\/](@radix-ui|lucide-react)[\\/]/,
          name: "ui",
          chunks: "all",
          priority: 20,
        },
      };
    }

    return config;
  },

  // Headers for security and performance
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
      {
        source: "/api/(.*)",
        headers: [
          {
            key: "Access-Control-Allow-Origin",
            value:
              process.env.NODE_ENV === "production"
                ? "https://eloquentai.vercel.app"
                : "http://localhost:3000",
          },
          {
            key: "Access-Control-Allow-Methods",
            value: "GET,OPTIONS,PATCH,DELETE,POST,PUT",
          },
          {
            key: "Access-Control-Allow-Headers",
            value:
              "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization",
          },
        ],
      },
    ];
  },

  // Redirects for better UX
  async redirects() {
    return [
      {
        source: "/chat",
        destination: "/",
        permanent: true,
      },
    ];
  },

  // Rewrites for API proxy in development
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/api/v1/:path*",
          destination:
            process.env.NODE_ENV === "development"
              ? "http://localhost:8000/v1/:path*"
              : "/api/v1/:path*",
        },
      ],
    };
  },

  // Output configuration for deployment
  output: "standalone",

  // TypeScript configuration
  typescript: {
    // Fail build on type errors in production
    ignoreBuildErrors: process.env.NODE_ENV === "development",
  },

  // ESLint configuration
  eslint: {
    // Fail build on lint errors in production
    ignoreDuringBuilds: process.env.NODE_ENV === "development",
  },
};

module.exports = nextConfig;
