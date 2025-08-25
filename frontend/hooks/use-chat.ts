"use client";

import { useChatManager } from "./use-chat-manager";

/**
 * Legacy useChat hook that now delegates to useChatManager.
 * Maintains backward compatibility while using the new chat management system.
 */
export function useChat(chatId: string | null) {
  const chatManager = useChatManager();

  // If a specific chatId is provided and it's different from current, select it
  if (chatId && chatId !== chatManager.currentChatId) {
    chatManager.selectChat(chatId);
  }

  return {
    messages: chatManager.messages,
    isLoading: chatManager.isLoading,
    isStreaming: chatManager.isStreaming,
    sendMessage: chatManager.sendMessage,
    error: chatManager.error,
    clearError: chatManager.clearError,
  };
}
