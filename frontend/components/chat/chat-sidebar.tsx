"use client";

import { useMemo } from "react";
import { Plus, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useChatManager } from "@/hooks/use-chat-manager";
import { cn } from "@/lib/utils";

interface ChatSidebarProps {
  onChatSelect?: (chatId: string) => void;
  onNewChat?: () => void;
}

export function ChatSidebar({ onChatSelect, onNewChat }: ChatSidebarProps) {
  const {
    chats,
    currentChatId,
    isLoading,
    error,
    createNewChat,
    selectChat,
    isSignedIn,
    isAuthLoaded,
    generateChatTitle,
  } = useChatManager();

  // Group chats by date for better organization
  const groupedChats = useMemo(() => {
    if (!chats.length) return {};

    const groups: Record<string, typeof chats> = {};
    const now = new Date();

    chats.forEach((chat) => {
      const chatDate = new Date(chat.created_at);
      const diffDays = Math.floor(
        (now.getTime() - chatDate.getTime()) / (1000 * 60 * 60 * 24),
      );

      let groupKey: string;
      if (diffDays === 0) {
        groupKey = "Today";
      } else if (diffDays === 1) {
        groupKey = "Yesterday";
      } else if (diffDays < 7) {
        groupKey = "This Week";
      } else if (diffDays < 30) {
        groupKey = "This Month";
      } else {
        groupKey = "Older";
      }

      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey]!.push(chat);
    });

    return groups;
  }, [chats]);

  const handleNewChat = async () => {
    const chatId = await createNewChat();
    if (chatId) {
      onNewChat?.();
    }
  };

  const handleChatSelect = async (chatId: string) => {
    await selectChat(chatId);
    onChatSelect?.(chatId);
  };

  const formatChatTitle = (chat: (typeof chats)[0]): string => {
    if (chat.title) return chat.title;
    if (chat.last_message_preview) {
      return generateChatTitle(chat.last_message_preview);
    }
    return `Chat ${chat.id.slice(-6)}`;
  };

  const formatChatTime = (chat: (typeof chats)[0]): string => {
    const date = new Date(chat.updated_at || chat.created_at);
    const now = new Date();
    const diffHours = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60),
    );

    if (diffHours < 1) return "Just now";
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  if (!isAuthLoaded) {
    return (
      <div className="border-r bg-card h-full flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="border-r bg-card h-full flex flex-col">
        {/* Header - Fixed to match main header height */}
        <div className="border-b h-16 flex items-center justify-between px-4">
          <h2 className="font-semibold text-lg">Chats</h2>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleNewChat}
                disabled={isLoading}
                className="h-8 w-8"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Start new chat</TooltipContent>
          </Tooltip>
        </div>

        {/* Sub-header with auth status */}
        {!isSignedIn && (
          <div className="px-4 py-2 border-b bg-muted/20">
            <div className="text-xs text-muted-foreground">
              Sign in for chat history
            </div>
          </div>
        )}

        {/* Chat list */}
        <ScrollArea className="flex-1">
          <div className="p-2">
            {isLoading && chats.length === 0 && (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </div>
            )}

            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md mb-2">
                {error}
              </div>
            )}

            {!isLoading && chats.length === 0 && !error && (
              <div className="text-center py-8 px-4">
                <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
                <div className="text-sm text-muted-foreground mb-3">
                  {isSignedIn
                    ? "No conversations yet. Start your first chat!"
                    : "No conversations. Sign in to save chat history."}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleNewChat}
                  disabled={isLoading}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  New Chat
                </Button>
              </div>
            )}

            {/* Render grouped chats */}
            {Object.entries(groupedChats).map(([groupName, groupChats]) => (
              <div key={groupName} className="mb-4">
                <div className="text-xs font-medium text-muted-foreground px-2 py-1 mb-2">
                  {groupName}
                </div>
                <div className="space-y-1">
                  {groupChats.map((chat) => (
                    <button
                      key={chat.id}
                      onClick={() => handleChatSelect(chat.id)}
                      className={cn(
                        "w-full text-left p-3 rounded-lg hover:bg-accent/50 transition-colors group",
                        "border border-transparent hover:border-border/50",
                        currentChatId === chat.id && "bg-accent border-border",
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="font-medium text-sm truncate mb-1">
                            {formatChatTitle(chat)}
                          </div>
                          {chat.last_message_preview && (
                            <div className="text-xs text-muted-foreground truncate">
                              {chat.last_message_preview}
                            </div>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground whitespace-nowrap">
                          {formatChatTime(chat)}
                        </div>
                      </div>

                      {/* Chat metadata */}
                      <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {chat.message_count && (
                            <span>{chat.message_count} messages</span>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="p-3 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={handleNewChat}
            disabled={isLoading}
            className="w-full"
          >
            <Plus className="h-4 w-4 mr-2" />
            {isLoading ? "Creating..." : "New Chat"}
          </Button>
        </div>
      </div>
    </TooltipProvider>
  );
}
