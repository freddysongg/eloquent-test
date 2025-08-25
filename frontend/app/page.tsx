"use client";

import { Suspense, useState } from "react";
import { ChatInterface } from "@/components/chat/chat-interface";
import { ChatSidebar } from "@/components/chat/chat-sidebar";
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
    <div className="flex h-screen bg-background relative">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex md:w-64 md:flex-col">
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-full">
              <LoadingSpinner />
            </div>
          }
        >
          <ChatSidebar
            onChatSelect={handleChatSelect}
            onNewChat={handleNewChat}
          />
        </Suspense>
      </div>

      {/* Main chat interface */}
      <div className="flex-1 flex flex-col">
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
