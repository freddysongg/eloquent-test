module.exports = {
  ci: {
    collect: {
      url: [
        "http://localhost:3000",
        "http://localhost:3000/login",
        "http://localhost:3000/register",
      ],
      numberOfRuns: 3,
      settings: {
        chromeFlags: "--no-sandbox --disable-dev-shm-usage",
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["error", { minScore: 0.8 }],
        "categories:accessibility": ["error", { minScore: 0.9 }],
        "categories:best-practices": ["error", { minScore: 0.8 }],
        "categories:seo": ["error", { minScore: 0.8 }],
        "categories:pwa": "off", // PWA not required for this project

        // Core Web Vitals
        "first-contentful-paint": ["error", { maxNumericValue: 2000 }],
        "largest-contentful-paint": ["error", { maxNumericValue: 2500 }],
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
        "total-blocking-time": ["error", { maxNumericValue: 300 }],

        // Additional performance metrics
        "speed-index": ["warn", { maxNumericValue: 3000 }],
        interactive: ["warn", { maxNumericValue: 3000 }],

        // Accessibility
        "color-contrast": "error",
        "image-alt": "error",
        label: "error",
        "landmark-one-h1": "error",

        // Best practices
        "is-on-https": "off", // Not applicable for localhost testing
        "uses-http2": "off", // Not applicable for localhost testing
        "no-vulnerable-libraries": "error",
        "csp-xss": "warn",

        // Bundle size warnings
        "total-byte-weight": ["warn", { maxNumericValue: 2048000 }], // 2MB
        "unused-javascript": ["warn", { maxNumericValue: 512000 }], // 500KB
      },
    },
    upload: {
      target: "temporary-public-storage",
    },
  },
};
