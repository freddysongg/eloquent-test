"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface MigrationData {
  anonymousSessionId: string;
  chatHistory: any[];
}

export function useAuthMigration() {
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const [migrationInProgress, setMigrationInProgress] = useState(false);
  const [migrationCompleted, setMigrationCompleted] = useState(false);

  // Mutation for migrating anonymous data to authenticated user
  const migrationMutation = useMutation({
    mutationFn: async (data: MigrationData) => {
      const token = await getToken();

      const response = await apiClient.post("/auth/migrate-anonymous", data, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      return response.data;
    },
    onSuccess: () => {
      setMigrationCompleted(true);
      // Clear anonymous session data from localStorage
      localStorage.removeItem("anonymous_session_id");
      localStorage.removeItem("anonymous_chat_history");
    },
    onError: (error) => {
      console.error("Migration failed:", error);
      setMigrationInProgress(false);
    },
  });

  // Auto-migrate when user signs in and has anonymous data
  useEffect(() => {
    const performMigration = async () => {
      if (
        isLoaded &&
        isSignedIn &&
        !migrationCompleted &&
        !migrationInProgress &&
        !migrationMutation.isPending
      ) {
        const anonymousSessionId = localStorage.getItem("anonymous_session_id");
        const anonymousChatHistory = localStorage.getItem(
          "anonymous_chat_history",
        );

        if (anonymousSessionId || anonymousChatHistory) {
          setMigrationInProgress(true);

          try {
            await migrationMutation.mutateAsync({
              anonymousSessionId: anonymousSessionId || "",
              chatHistory: anonymousChatHistory
                ? JSON.parse(anonymousChatHistory)
                : [],
            });
          } catch (error) {
            // Migration failed, but user is still authenticated
            setMigrationInProgress(false);
          }
        }
      }
    };

    performMigration();
  }, [isLoaded, isSignedIn, migrationCompleted, migrationInProgress]);

  return {
    migrationInProgress,
    migrationCompleted,
    migrationError: migrationMutation.error,
    retryMigration: () => {
      setMigrationInProgress(false);
      setMigrationCompleted(false);
    },
  };
}
