"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChatSidebar } from "./chat-sidebar";
import { cn } from "@/lib/utils";

interface MobileSidebarButtonProps {
  onChatSelect: (chatId: string) => void;
  onNewChat: () => void;
}

/**
 * Mobile sidebar button and overlay - only renders on mobile
 * Integrates with ChatHeader to provide mobile navigation
 */
export function MobileSidebarButton({
  onChatSelect,
  onNewChat,
}: MobileSidebarButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleChatSelect = (chatId: string) => {
    onChatSelect(chatId);
    setIsOpen(false); // Close sidebar after selection
  };

  const handleNewChat = () => {
    onNewChat();
    setIsOpen(false); // Close sidebar after creating new chat
  };

  return (
    <>
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden h-9 w-9"
        onClick={() => setIsOpen(true)}
        aria-label="Open navigation menu"
        aria-expanded={isOpen}
        aria-controls="mobile-sidebar"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Mobile sidebar overlay */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
            onClick={() => setIsOpen(false)}
          />

          {/* Sidebar */}
          <div
            id="mobile-sidebar"
            className={cn(
              "fixed top-0 left-0 h-full w-80 z-50 transform transition-transform duration-300 ease-in-out md:hidden",
              isOpen ? "translate-x-0" : "-translate-x-full",
            )}
            role="dialog"
            aria-label="Chat navigation"
          >
            <div className="relative h-full">
              <ChatSidebar
                onChatSelect={handleChatSelect}
                onNewChat={handleNewChat}
              />

              {/* Close button */}
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-4 right-4 h-8 w-8"
                onClick={() => setIsOpen(false)}
                aria-label="Close navigation menu"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
