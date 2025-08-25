/**
 * API client utilities for communicating with the backend.
 * Handles chat operations, authentication, and request/response processing.
 */

import {
  ChatListResponse,
  ChatResponse,
  ChatDetailResponse,
  SendMessageRequest,
  SendMessageResponse,
} from "@/types/chat";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * API client class for handling HTTP requests to the backend
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Get authentication headers including Clerk JWT token
   */
  private async getAuthHeaders(): Promise<HeadersInit> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    // Try to get Clerk auth token if available
    if (typeof window !== "undefined" && window.Clerk) {
      try {
        const token = await window.Clerk.session?.getToken();
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }
      } catch (error) {
        console.warn("Failed to get auth token:", error);
      }
    }

    return headers;
  }

  /**
   * Make authenticated HTTP request
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = await this.getAuthHeaders();

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
  }

  /**
   * List user's chat conversations
   */
  async listChats(): Promise<ChatListResponse> {
    return this.request<ChatListResponse>("/api/v1/chats/");
  }

  /**
   * Create a new chat conversation
   */
  async createChat(): Promise<ChatResponse> {
    return this.request<ChatResponse>("/api/v1/chats/", {
      method: "POST",
    });
  }

  /**
   * Get specific chat with message history
   */
  async getChat(chatId: string): Promise<ChatDetailResponse> {
    return this.request<ChatDetailResponse>(`/api/v1/chats/${chatId}`);
  }

  /**
   * Send message to chat (non-streaming)
   */
  async sendMessage(
    chatId: string,
    request: SendMessageRequest,
  ): Promise<SendMessageResponse> {
    return this.request<SendMessageResponse>(
      `/api/v1/chats/${chatId}/messages`,
      {
        method: "POST",
        body: JSON.stringify(request),
      },
    );
  }

  /**
   * Send message to chat with streaming response
   */
  async sendMessageStreaming(
    chatId: string,
    request: SendMessageRequest,
  ): Promise<ReadableStream<Uint8Array>> {
    const url = `${this.baseUrl}/api/v1/chats/${chatId}/messages`;
    const headers = await this.getAuthHeaders();

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({ ...request, stream: true }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error("No response body available for streaming");
    }

    return response.body;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Declare global Clerk interface for TypeScript
declare global {
  interface Window {
    Clerk?: {
      session?: {
        getToken: () => Promise<string>;
      };
    };
  }
}
