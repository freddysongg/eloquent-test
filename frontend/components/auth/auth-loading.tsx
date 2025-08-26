"use client";

import { useAuth } from "@/components/providers/auth-provider";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

interface AuthLoadingProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  loadingMessage?: string;
}

/**
 * Authentication loading wrapper that handles loading states and errors
 * Provides smooth transitions during authentication state changes
 */
export function AuthLoading({
  children,
  fallback,
  loadingMessage = "Initializing authentication...",
}: AuthLoadingProps) {
  const { isLoaded, migrationInProgress, migrationError } = useAuth();

  // Show loading state while auth is initializing
  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="p-6">
            <div className="text-center space-y-4">
              <LoadingSpinner />
              <div>
                <p className="text-sm font-medium">{loadingMessage}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Setting up secure authentication...
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show migration progress if user data is being migrated
  if (migrationInProgress) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="p-6">
            <div className="text-center space-y-4">
              <LoadingSpinner />
              <div>
                <p className="text-sm font-medium">Migrating your data...</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Transferring your chat history to your new account
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show migration error if it occurred
  if (migrationError) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md border-destructive/20 bg-destructive/5">
          <CardContent className="p-6">
            <div className="text-center space-y-4">
              <AlertCircle className="w-8 h-8 text-destructive mx-auto" />
              <div>
                <p className="text-sm font-medium text-destructive">
                  Migration Error
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {migrationError.message || "Failed to migrate your data"}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Your account is still active. Previous data may not be
                  available.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show fallback component if provided
  if (fallback) {
    return <>{fallback}</>;
  }

  // Render children when auth is ready
  return <>{children}</>;
}
