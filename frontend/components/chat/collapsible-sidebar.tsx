"use client";

import { useMemo } from "react";
import { Plus, MessageSquare, ChevronLeft, ChevronRight } from "lucide-react";
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
import { useSidebar } from "@/hooks/use-sidebar";
import { Chat } from "@/types/chat";
import { cn } from "@/lib/utils";

interface CollapsibleSidebarProps {
  onChatSelect?: (chatId: string) => void;
  onNewChat?: () => void;
}

export function CollapsibleSidebar({
  onChatSelect,
  onNewChat,
}: CollapsibleSidebarProps) {
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

  const { isCollapsed, width, toggleCollapsed, isMobile } = useSidebar();

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

  // Don't render anything on mobile - mobile sidebar is handled elsewhere
  if (isMobile) {
    return null;
  }

  // Desktop version with collapse/expand
  return (
    <TooltipProvider>
      <div
        className="relative h-full bg-card border-r transition-all duration-300 ease-in-out"
        style={{ width: `${width}px` }}
      >
        <div id="desktop-sidebar-content" className="flex flex-col h-full">
          {/* Header */}
          <div className="border-b h-16 flex items-center justify-between px-4">
            {!isCollapsed ? (
              <>
                <h2 className="font-semibold text-lg">Chats</h2>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={toggleCollapsed}
                      className="h-8 w-8"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Collapse sidebar</TooltipContent>
                </Tooltip>
              </>
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleCollapsed}
                    className="h-8 w-8 mx-auto"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Expand sidebar</TooltipContent>
              </Tooltip>
            )}
          </div>

          {/* Auth status */}
          {!(isSignedIn ?? false) && !isCollapsed && (
            <div className="px-4 py-2 border-b bg-muted/20">
              <div className="text-xs text-muted-foreground">
                Sign in for chat history
              </div>
            </div>
          )}

          {/* Chat list */}
          <ScrollArea className="flex-1">
            <div className={cn("p-2", isCollapsed && "px-1")}>
              {isLoading && chats.length === 0 && (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              )}

              {!isLoading && chats.length === 0 && !error && (
                <div className="text-center py-8 px-2">
                  <MessageSquare
                    className={cn(
                      "mx-auto text-muted-foreground/50 mb-3",
                      isCollapsed ? "h-6 w-6" : "h-12 w-12",
                    )}
                  />
                  {!isCollapsed && (
                    <>
                      <div className="text-sm text-muted-foreground mb-3">
                        {(isSignedIn ?? false)
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
                    </>
                  )}
                </div>
              )}

              {/* Render grouped chats */}
              {Object.entries(groupedChats).map(([groupName, groupChats]) => (
                <div key={groupName} className="mb-4">
                  {!isCollapsed && (
                    <div className="text-xs font-medium text-muted-foreground px-2 py-1 mb-2">
                      {groupName}
                    </div>
                  )}
                  <div className="space-y-1">
                    {groupChats.map((chat) => (
                      <ChatItem
                        key={chat.id}
                        chat={chat}
                        isActive={currentChatId === chat.id}
                        isCollapsed={isCollapsed}
                        onSelect={() => handleChatSelect(chat.id)}
                        formatTitle={formatChatTitle}
                        formatTime={formatChatTime}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      </div>
    </TooltipProvider>
  );
}

// Separate component for individual chat items
interface ChatItemProps {
  chat: Chat;
  isActive: boolean;
  isCollapsed: boolean;
  onSelect: () => void;
  formatTitle: (chat: Chat) => string;
  formatTime: (chat: Chat) => string;
}

function ChatItem({
  chat,
  isActive,
  isCollapsed,
  onSelect,
  formatTitle,
  formatTime,
}: ChatItemProps) {
  if (isCollapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={onSelect}
            className={cn(
              "w-full p-2 rounded-lg hover:bg-accent/50 transition-colors",
              "border border-transparent hover:border-border/50 flex items-center justify-center",
              isActive && "bg-accent border-border",
            )}
          >
            <MessageSquare className="h-5 w-5 text-muted-foreground" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">
          <div className="max-w-48">
            <div className="font-medium text-sm mb-1">{formatTitle(chat)}</div>
            <div className="text-xs text-muted-foreground">
              {formatTime(chat)}
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    );
  }

  return (
    <button
      onClick={onSelect}
      className={cn(
        "w-full text-left p-3 rounded-lg hover:bg-accent/50 transition-colors group",
        "border border-transparent hover:border-border/50",
        isActive && "bg-accent border-border",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="font-medium text-sm truncate mb-1">
            {formatTitle(chat)}
          </div>
          {chat.last_message_preview && (
            <div className="text-xs text-muted-foreground truncate">
              {chat.last_message_preview}
            </div>
          )}
        </div>
        <div className="text-xs text-muted-foreground whitespace-nowrap">
          {formatTime(chat)}
        </div>
      </div>

      {/* Chat metadata */}
      <div className="flex items-center justify-between mt-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {chat.message_count && <span>{chat.message_count} messages</span>}
        </div>
      </div>
    </button>
  );
}
