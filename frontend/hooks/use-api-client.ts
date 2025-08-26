"use client";

import { useAuth } from "@clerk/nextjs";
import { useMemo } from "react";
import {
  ChatListResponse,
  ChatResponse,
  ChatDetailResponse,
  SendMessageRequest,
  SendMessageResponse,
} from "@/types/chat";

/**
 * Authentication-aware API client hook
 * Creates an API client instance with proper authentication headers
 */
export function useApiClient() {
  const { getToken, isSignedIn, isLoaded } = useAuth();

  const apiClient = useMemo(() => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    /**
     * Get authentication headers including Clerk JWT token
     */
    const getAuthHeaders = async (): Promise<HeadersInit> => {
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };

      if (isSignedIn && isLoaded) {
        try {
          const token = await getToken();
          if (token) {
            headers.Authorization = `Bearer ${token}`;
          }
        } catch (error) {
          console.warn("Failed to get auth token:", error);
        }
      }

      return headers;
    };

    /**
     * Make authenticated HTTP request
     */
    const request = async <T>(
      endpoint: string,
      options: RequestInit = {},
    ): Promise<T> => {
      const url = `${baseUrl}${endpoint}`;
      const headers = await getAuthHeaders();

      try {
        const response = await fetch(url, {
          ...options,
          headers: {
            ...headers,
            ...options.headers,
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        console.error(`API request failed for ${endpoint}:`, error);
        throw error;
      }
    };

    return {
      // Chat operations
      listChats: () => request<ChatListResponse>("/v1/chats/"),
      createChat: () => request<ChatResponse>("/v1/chats/", { method: "POST" }),
      getChat: (chatId: string) =>
        request<ChatDetailResponse>(`/v1/chats/${chatId}`),
      sendMessage: (chatId: string, data: SendMessageRequest) =>
        request<SendMessageResponse>(`/v1/chats/${chatId}/messages`, {
          method: "POST",
          body: JSON.stringify(data),
        }),

      // Streaming message
      sendMessageStreaming: async (
        chatId: string,
        data: SendMessageRequest,
      ) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${baseUrl}/v1/chats/${chatId}/messages`, {
          method: "POST",
          headers,
          body: JSON.stringify({ ...data, stream: true }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error("No response body available for streaming");
        }

        return response.body;
      },

      // Authentication state
      isAuthenticated: isSignedIn && isLoaded,
      isLoaded,
    };
  }, [getToken, isSignedIn, isLoaded]);

  return apiClient;
}
