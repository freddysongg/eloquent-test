"use client";

import { createContext, useContext, useEffect } from "react";
import { useAuth as useClerkAuth, useUser } from "@clerk/nextjs";
import { useAuthMigration } from "@/hooks/use-auth-migration";

interface AuthContextType {
  user: ReturnType<typeof useUser>["user"];
  isLoaded: boolean;
  isSignedIn: boolean | undefined;
  signOut: () => Promise<void>;
  migrationInProgress: boolean;
  migrationCompleted: boolean;
  migrationError: Error | null;
  retryMigration: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { isLoaded: authLoaded, isSignedIn, signOut } = useClerkAuth();
  const { user, isLoaded: userLoaded } = useUser();
  const {
    migrationInProgress,
    migrationCompleted,
    migrationError,
    retryMigration,
  } = useAuthMigration();

  const isLoaded = authLoaded && userLoaded;

  // Log authentication state changes in development
  useEffect(() => {
    if (process.env.NODE_ENV === "development" && isLoaded) {
      console.log("Auth state:", {
        isSignedIn,
        user: user
          ? { id: user.id, emailAddresses: user.emailAddresses }
          : null,
        migrationInProgress,
        migrationCompleted,
      });
    }
  }, [isLoaded, isSignedIn, user, migrationInProgress, migrationCompleted]);

  const value: AuthContextType = {
    user,
    isLoaded,
    isSignedIn,
    signOut,
    migrationInProgress,
    migrationCompleted,
    migrationError,
    retryMigration,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
