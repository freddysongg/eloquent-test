/**
 * Chat management hook for handling chat state, API interactions, and real-time updates.
 * Manages chat list, current chat selection, message history, and API operations.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api";
import { Chat, Message, ChatState } from "@/types/chat";
import { useAuth } from "@/components/providers/auth-provider";

export function useChatManager() {
  const { isSignedIn, isLoaded } = useAuth();

  const [state, setState] = useState<ChatState>({
    chats: [],
    currentChatId: null,
    messages: [],
    isLoading: false,
    isStreaming: false,
    error: null,
  });

  /**
   * Load user's chat list from the API
   */
  const loadChats = useCallback(async () => {
    if (!isLoaded) return;

    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      const response = await apiClient.listChats();

      if (response.error) {
        throw new Error(response.error);
      }

      setState((prev) => ({
        ...prev,
        chats: response.data.chats,
        isLoading: false,
      }));
    } catch (error) {
      console.error("Failed to load chats:", error);
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Failed to load chats",
        isLoading: false,
      }));
    }
  }, [isLoaded]);

  /**
   * Create a new chat conversation
   */
  const createNewChat = useCallback(async (): Promise<string | null> => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      const response = await apiClient.createChat();

      if (response.error) {
        throw new Error(response.error);
      }

      const newChat: Chat = {
        id: response.data.chat_id,
        created_at: response.data.created_at,
        message_count: 0,
      };

      setState((prev) => ({
        ...prev,
        chats: [newChat, ...prev.chats],
        currentChatId: newChat.id,
        messages: [],
        isLoading: false,
      }));

      return newChat.id;
    } catch (error) {
      console.error("Failed to create chat:", error);
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Failed to create chat",
        isLoading: false,
      }));
      return null;
    }
  }, []);

  /**
   * Select and load a chat conversation
   */
  const selectChat = useCallback(
    async (chatId: string) => {
      if (chatId === state.currentChatId) return;

      try {
        setState((prev) => ({ ...prev, isLoading: true, error: null }));

        const response = await apiClient.getChat(chatId);

        if (response.error) {
          throw new Error(response.error);
        }

        setState((prev) => ({
          ...prev,
          currentChatId: chatId,
          messages: response.data.messages,
          isLoading: false,
        }));
      } catch (error) {
        console.error("Failed to load chat:", error);
        setState((prev) => ({
          ...prev,
          error: error instanceof Error ? error.message : "Failed to load chat",
          isLoading: false,
        }));
      }
    },
    [state.currentChatId],
  );

  /**
   * Send a message to the current chat
   */
  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
      if (!content.trim()) return;

      // If no current chat, create one
      let chatId = state.currentChatId;
      if (!chatId) {
        chatId = await createNewChat();
        if (!chatId) return; // Failed to create chat
      }

      // Add user message immediately (optimistic update)
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: content.trim(),
        timestamp: new Date(),
      };

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
        isStreaming: true,
        error: null,
      }));

      try {
        // For now, use non-streaming API (Phase 3 will implement streaming)
        const response = await apiClient.sendMessage(chatId, {
          message: content.trim(),
          stream: false,
        });

        if (response.error) {
          throw new Error(response.error);
        }

        // Add assistant response
        if (response.data.response) {
          const assistantMessage: Message = {
            id: response.data.message_id,
            role: "assistant",
            content: response.data.response,
            timestamp: new Date(),
          };

          setState((prev) => ({
            ...prev,
            messages: [...prev.messages, assistantMessage],
            isStreaming: false,
          }));

          // Update chat list with new message info
          setState((prev) => ({
            ...prev,
            chats: prev.chats.map((chat) =>
              chat.id === chatId
                ? {
                    ...chat,
                    last_message_preview:
                      content.slice(0, 50) + (content.length > 50 ? "..." : ""),
                    message_count: (chat.message_count || 0) + 2, // +2 for user + assistant
                    updated_at: new Date().toISOString(),
                  }
                : chat,
            ),
          }));
        }
      } catch (error) {
        console.error("Failed to send message:", error);

        // Remove the optimistic user message on error
        setState((prev) => ({
          ...prev,
          messages: prev.messages.filter((m) => m.id !== userMessage.id),
          error:
            error instanceof Error ? error.message : "Failed to send message",
          isStreaming: false,
        }));
      }
    },
    [state.currentChatId, createNewChat],
  );

  /**
   * Clear current error
   */
  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  /**
   * Generate chat title from first message
   */
  const generateChatTitle = useCallback((firstMessage: string): string => {
    if (!firstMessage) return "New Chat";

    // Take first 30 characters and clean up
    let title = firstMessage.slice(0, 30).trim();
    if (firstMessage.length > 30) {
      title += "...";
    }

    return title;
  }, []);

  // Load chats on mount and auth state change
  useEffect(() => {
    if (isLoaded) {
      loadChats();
    }
  }, [isLoaded, loadChats]);

  return {
    // State
    chats: state.chats,
    currentChatId: state.currentChatId,
    messages: state.messages,
    isLoading: state.isLoading,
    isStreaming: state.isStreaming,
    error: state.error,

    // Actions
    createNewChat,
    selectChat,
    sendMessage,
    loadChats,
    clearError,
    generateChatTitle,

    // Auth state
    isSignedIn,
    isAuthLoaded: isLoaded,
  };
}
