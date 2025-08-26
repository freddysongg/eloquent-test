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
    setCurrentChatId(null);
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Desktop Collapsible Sidebar */}
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

      {/* Main chat interface - mobile sidebar is handled within ChatInterface */}
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
    </div>
  );
}
