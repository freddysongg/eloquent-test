'use client';

import { useState } from 'react';

// TODO: Replace with actual message types
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function useChat(chatId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  // chatId will be used to fetch/send messages to the specific chat
  // when the actual API implementation is completed
  const sendMessage = async (content: string) => {
    // Add user message immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setIsStreaming(true);

    try {
      // TODO: Implement actual API call to backend
      // Will use chatId to send message to the correct chat endpoint
      // e.g., POST /api/chats/${chatId}/messages
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Simulate assistant response
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: 'This is a placeholder response. The Integration Agent will implement the actual Claude API streaming.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      // TODO: Handle error state
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  return {
    messages,
    isLoading,
    isStreaming,
    sendMessage,
  };
}