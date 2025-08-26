"use client";

import { Suspense, useState } from "react";
import { ChatInterface } from "@/components/chat/chat-interface";
import { CollapsibleSidebar } from "@/components/chat/collapsible-sidebar";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

export default function HomePage() {
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);

  const handleChatSelect = (chatId: string) => {
    setCurrentChatId(chatId);
  };

  const handleNewChat = () => {
    // New chat will be handled by the useChatManager hook
    setCurrentChatId(null);
  };

  return (
    <div className="flex h-screen bg-background flex-col">
      {/* Main Content */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Collapsible Sidebar - handles both desktop and mobile */}
        <div className="hidden md:block">
          <Suspense
            fallback={
              <div className="w-64 h-full flex items-center justify-center border-r bg-card">
                <LoadingSpinner />
              </div>
            }
          >
            <CollapsibleSidebar
              onChatSelect={handleChatSelect}
              onNewChat={handleNewChat}
            />
          </Suspense>
        </div>

        {/* Main chat interface */}
        <div className="flex-1 flex flex-col min-w-0">
          <Suspense
            fallback={
              <div className="flex items-center justify-center h-full">
                <LoadingSpinner />
              </div>
            }
          >
            <ChatInterface
              currentChatId={currentChatId}
              onChatSelect={handleChatSelect}
            />
          </Suspense>
        </div>

        {/* Mobile sidebar is rendered within CollapsibleSidebar component */}
      </div>
    </div>
  );
}
