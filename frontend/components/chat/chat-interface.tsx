'use client';

import { useState } from 'react';
import { MessageList } from '@/components/chat/message-list';
import { MessageInput } from '@/components/chat/message-input';
import { ChatHeader } from '@/components/chat/chat-header';
import { useChat } from '@/hooks/use-chat';
import { useAuth } from '@/components/providers/auth-provider';

export function ChatInterface() {
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const { user, isLoaded } = useAuth();
  
  const {
    messages,
    isLoading,
    sendMessage,
    isStreaming,
  } = useChat(currentChatId);

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;
    
    try {
      await sendMessage(content);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <ChatHeader 
        user={user}
        isConnected={true} // TODO: Get from socket provider
        onNewChat={() => setCurrentChatId(null)}
      />
      
      <MessageList 
        messages={messages}
        isLoading={isLoading}
        isStreaming={isStreaming}
      />
      
      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={isStreaming}
        placeholder={
          user 
            ? "Ask me about fintech services..." 
            : "Ask me about fintech services (sign in for chat history)"
        }
      />
    </div>
  );
}