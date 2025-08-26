"use client";

import { MessageList } from "@/components/chat/message-list";
import { MessageInput } from "@/components/chat/message-input";
import { ChatHeader } from "@/components/chat/chat-header";
import { MigrationBanner } from "@/components/auth/migration-banner";
import { MobileAuthBanner } from "@/components/auth/mobile-auth-banner";
import { AuthLoading } from "@/components/auth/auth-loading";
import { useChatManager } from "@/hooks/use-chat-manager";
import { useSocket } from "@/components/providers/socket-provider";

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
    error,
    clearError,
  } = useChatManager();

  const { isConnected } = useSocket();

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

  return (
    <AuthLoading loadingMessage="Loading chat interface...">
      <div className="flex flex-col h-full bg-gradient-background-subtle">
        {/* Chat Header */}
        <ChatHeader
          user={isSignedIn ? { isSignedIn } : null}
          isConnected={isConnected}
          onNewChat={handleNewChat}
          {...(onChatSelect && { onChatSelect })}
          {...(currentChatId !== undefined && { currentChatId })}
        />

        {/* Mobile auth banner for small screens */}
        <MobileAuthBanner />

        {/* Migration banner for anonymous users on desktop */}
        <MigrationBanner className="hidden md:block mx-4 md:mx-6 mt-3" />

        {/* Error display with enhanced styling */}
        {error && (
          <div className="mx-4 md:mx-6 mt-2 p-4 rounded-lg bg-gradient-destructive/10 border border-destructive/20 shadow-sm animate-in slide-in-from-top-2">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2 flex-1">
                <div className="w-5 h-5 rounded-full bg-destructive/20 flex-shrink-0 flex items-center justify-center mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-destructive" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-destructive-foreground mb-1">
                    Something went wrong
                  </div>
                  <div className="text-sm text-destructive/80">{error}</div>
                </div>
              </div>
              <button
                onClick={clearError}
                className="text-xs text-destructive hover:text-destructive-foreground hover:bg-destructive/10 px-2 py-1 rounded transition-colors"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Main chat area with optimized layout */}
        <div className="flex-1 flex flex-col min-h-0">
          <MessageList
            messages={messages}
            isLoading={isLoading}
            isStreaming={isStreaming}
          />
        </div>

        {/* Enhanced message input */}
        <MessageInput
          onSendMessage={handleSendMessage}
          disabled={isStreaming}
          placeholder={
            isSignedIn
              ? "Ask me about fintech services..."
              : "Ask me about fintech services (sign in for chat history)"
          }
          maxLength={2000}
          onStop={() => {
            // TODO: Implement stop functionality in Phase 3
            console.log("Stop streaming requested");
          }}
        />
      </div>
    </AuthLoading>
  );
}
