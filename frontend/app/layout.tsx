import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { Providers } from "@/components/providers/providers";
import { Toaster } from "@/components/ui/toaster";
import "@/app/globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Eloquent AI - Fintech FAQ Assistant",
    template: "%s | Eloquent AI",
  },
  description:
    "AI-powered chatbot with retrieval-augmented generation for accurate, context-aware responses to fintech FAQ queries.",
  keywords: [
    "AI chatbot",
    "fintech",
    "FAQ assistant",
    "customer support",
    "artificial intelligence",
    "machine learning",
  ],
  authors: [{ name: "Eloquent AI Team" }],
  creator: "Eloquent AI",
  publisher: "Eloquent AI",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  ),
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "/",
    title: "Eloquent AI - Fintech FAQ Assistant",
    description:
      "AI-powered chatbot for fintech FAQ support with real-time streaming responses.",
    siteName: "Eloquent AI",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Eloquent AI - Fintech FAQ Assistant",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Eloquent AI - Fintech FAQ Assistant",
    description:
      "AI-powered chatbot for fintech FAQ support with real-time streaming responses.",
    images: ["/twitter-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  ...(process.env.GOOGLE_SITE_VERIFICATION && {
    verification: {
      google: process.env.GOOGLE_SITE_VERIFICATION,
    },
  }),
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider
      appearance={{
        variables: {
          colorPrimary: "hsl(var(--primary))",
          colorBackground: "hsl(var(--background))",
          colorText: "hsl(var(--foreground))",
          colorInputBackground: "hsl(var(--background))",
          colorInputText: "hsl(var(--foreground))",
        },
        elements: {
          formButtonPrimary:
            "bg-primary text-primary-foreground hover:bg-primary/90",
          card: "bg-card border border-border",
          headerTitle: "text-foreground",
          headerSubtitle: "text-muted-foreground",
        },
      }}
    >
      <html lang="en" className={inter.variable} suppressHydrationWarning>
        <head>
          <meta
            name="viewport"
            content="width=device-width, initial-scale=1, viewport-fit=cover"
          />
          <meta name="theme-color" content="hsl(var(--background))" />
          <link rel="icon" href="/favicon.ico" sizes="any" />
          <link rel="icon" href="/icon.svg" type="image/svg+xml" />
          <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
          <link rel="manifest" href="/manifest.json" />
        </head>
        <body
          className={`${inter.className} font-sans antialiased min-h-screen bg-background text-foreground`}
          suppressHydrationWarning
        >
          <Providers>
            <div className="relative flex min-h-screen flex-col">
              <div className="flex-1">{children}</div>
            </div>
            <Toaster />
          </Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
