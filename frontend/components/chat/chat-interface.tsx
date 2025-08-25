"use client";

import { MessageList } from "@/components/chat/message-list";
import { MessageInput } from "@/components/chat/message-input";
import { ChatHeader } from "@/components/chat/chat-header";
import { useChatManager } from "@/hooks/use-chat-manager";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

interface ChatInterfaceProps {
  currentChatId?: string | null;
  onChatSelect?: (chatId: string) => void;
}

export function ChatInterface({
  currentChatId,
  onChatSelect,
}: ChatInterfaceProps) {
  const {
    messages,
    isLoading,
    sendMessage,
    isStreaming,
    createNewChat,
    isSignedIn,
    isAuthLoaded,
    error,
    clearError,
  } = useChatManager();

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;

    // Clear any previous errors
    if (error) {
      clearError();
    }

    try {
      await sendMessage(content);
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const handleNewChat = async () => {
    await createNewChat();
  };

  if (!isAuthLoaded) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <ChatHeader
        user={isSignedIn ? { isSignedIn } : null} // Simplified user prop
        isConnected={true} // TODO: Get from socket provider when implemented
        onNewChat={handleNewChat}
        {...(onChatSelect && { onChatSelect })}
        {...(currentChatId !== undefined && { currentChatId })}
      />

      {/* Error display */}
      {error && (
        <div className="mx-4 mt-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md border border-destructive/20">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={clearError}
              className="text-xs hover:underline ml-2"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <MessageList
        messages={messages}
        isLoading={isLoading}
        isStreaming={isStreaming}
      />

      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={isStreaming}
        placeholder={
          isSignedIn
            ? "Ask me about fintech services..."
            : "Ask me about fintech services (sign in for chat history)"
        }
      />
    </div>
  );
}
