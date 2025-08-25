"use client";

import { Button } from "@/components/ui/button";
import { PlusIcon } from "lucide-react";
import { MobileSidebar } from "./mobile-sidebar";
import { useAuth } from "@/components/providers/auth-provider";

interface ChatHeaderProps {
  user?: { isSignedIn: boolean } | null;
  isConnected: boolean;
  onNewChat: () => void;
  onChatSelect?: (chatId: string) => void;
  currentChatId?: string | null;
}

export function ChatHeader({
  isConnected,
  onNewChat,
  onChatSelect,
  currentChatId,
}: ChatHeaderProps) {
  const { user, isSignedIn } = useAuth();

  // Generate a dynamic title based on current context
  const getTitle = () => {
    if (currentChatId) {
      return "Eloquent AI"; // Could be enhanced to show chat title
    }
    return "Eloquent AI";
  };

  return (
    <div className="border-b bg-background/80 backdrop-blur-sm px-4 md:px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {/* Mobile sidebar menu - only show if onChatSelect is provided */}
          {onChatSelect && (
            <MobileSidebar onChatSelect={onChatSelect} onNewChat={onNewChat} />
          )}

          <h1 className="text-xl font-semibold">{getTitle()}</h1>
          <div
            className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
              isConnected
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
                : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300"
            }`}
          >
            {isConnected ? "Connected" : "Disconnected"}
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onNewChat}
            className="hidden md:flex"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            New Chat
          </Button>
          {isSignedIn && user ? (
            <div className="text-sm text-muted-foreground hidden sm:block">
              {user.firstName ||
                user.emailAddresses?.[0]?.emailAddress ||
                "User"}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground hidden sm:block">
              Anonymous User
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
