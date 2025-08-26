"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  redirectTo?: string;
  requireAuth?: boolean;
}

/**
 * AuthGuard component for protecting routes and handling authentication states
 *
 * Features:
 * - Route protection for authenticated-only content
 * - Loading states during authentication checks
 * - Automatic redirects for unauthenticated users
 * - Custom fallback components
 */
export function AuthGuard({
  children,
  fallback,
  redirectTo = "/sign-in",
  requireAuth = false,
}: AuthGuardProps) {
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoaded && requireAuth && !isSignedIn) {
      // Add current path as redirect parameter
      const currentPath = window.location.pathname + window.location.search;
      const redirectUrl = `${redirectTo}?redirect_url=${encodeURIComponent(currentPath)}`;
      router.push(redirectUrl);
    }
  }, [isLoaded, isSignedIn, requireAuth, redirectTo, router]);

  // Show loading state while authentication is being determined
  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <LoadingSpinner />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Show fallback or redirect if authentication is required but user is not signed in
  if (requireAuth && !isSignedIn) {
    if (fallback) {
      return <>{fallback}</>;
    }
    // Component will redirect via useEffect, show loading for now
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <LoadingSpinner />
          <p className="text-muted-foreground">Redirecting to sign in...</p>
        </div>
      </div>
    );
  }

  // Render children for public routes or authenticated users
  return <>{children}</>;
}

/**
 * Higher-order component for wrapping pages with authentication requirements
 */
export function withAuthGuard<P extends object>(
  Component: React.ComponentType<P>,
  options: {
    requireAuth?: boolean;
    redirectTo?: string;
    fallback?: React.ReactNode;
  } = {},
) {
  return function AuthGuardedComponent(props: P) {
    return (
      <AuthGuard {...options}>
        <Component {...props} />
      </AuthGuard>
    );
  };
}
