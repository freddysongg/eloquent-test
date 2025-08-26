"use client";

import { Button } from "@/components/ui/button";
import { PlusIcon, LogIn, UserPlus } from "lucide-react";
import { MobileSidebarButton } from "./mobile-sidebar";
import { UserButton, useAuth as useClerkAuth } from "@clerk/nextjs";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { useSidebar } from "@/hooks/use-sidebar";
import Link from "next/link";

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
  const { isSignedIn: isClerkSignedIn, isLoaded } = useClerkAuth();
  const { isCollapsed, isMobile } = useSidebar();

  const getTitle = () => {
    if (currentChatId) {
      return "Eloquent AI";
    }
    return "Eloquent AI";
  };

  return (
    <div className="border-b bg-background/80 backdrop-blur-sm">
      <div className="flex items-center justify-between h-16 px-4 md:px-6">
        <div className="flex items-center gap-4">
          {/* Mobile sidebar button - only shows on mobile */}
          {onChatSelect && (
            <MobileSidebarButton
              onChatSelect={onChatSelect}
              onNewChat={onNewChat}
            />
          )}

          <h1 className="text-xl font-semibold">{getTitle()}</h1>
          <div
            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
              isConnected
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
                : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300"
            }`}
          >
            {isConnected ? "Connected" : "Disconnected"}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Show New Chat button on mobile, or on desktop when sidebar is collapsed */}
          <Button
            variant="outline"
            size="sm"
            onClick={onNewChat}
            className={`${isMobile || isCollapsed ? "flex" : "hidden"} items-center gap-2`}
          >
            <PlusIcon className="h-4 w-4" />
            New Chat
          </Button>

          {/* Theme Toggle */}
          <ThemeToggle />

          {/* Authentication Section */}
          {isLoaded && (
            <>
              {isClerkSignedIn ? (
                <UserButton
                  appearance={{
                    elements: {
                      avatarBox: "w-8 h-8",
                      userButtonPopoverCard: "bg-card border-border",
                      userButtonPopoverActionButton:
                        "text-foreground hover:bg-muted",
                      userButtonPopoverActionButtonText: "text-foreground",
                      userButtonPopoverActionButtonIcon:
                        "text-muted-foreground",
                      userPreviewSecondaryIdentifier: "text-muted-foreground",
                    },
                  }}
                  afterSignOutUrl="/"
                  userProfileMode="navigation"
                  userProfileUrl="/profile"
                />
              ) : (
                <>
                  <div className="text-sm text-muted-foreground hidden sm:block">
                    Anonymous User
                  </div>
                  <div
                    className="flex items-center gap-2"
                    role="group"
                    aria-label="Authentication options"
                  >
                    <Button variant="ghost" size="sm" asChild>
                      <Link
                        href="/sign-in"
                        aria-label="Sign in to your account"
                      >
                        <span className="flex items-center gap-2">
                          <LogIn className="w-4 h-4" aria-hidden="true" />
                          <span>Sign In</span>
                        </span>
                      </Link>
                    </Button>
                    <Button size="sm" asChild>
                      <Link href="/sign-up" aria-label="Create a new account">
                        <span className="flex items-center gap-2">
                          <UserPlus className="w-4 h-4" aria-hidden="true" />
                          <span>Sign Up</span>
                        </span>
                      </Link>
                    </Button>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
