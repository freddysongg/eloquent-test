/**
 * Chat-related TypeScript interfaces and types.
 * Defines the data structures for chat conversations, messages, and API responses.
 */

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export interface Chat {
  id: string;
  title?: string;
  created_at: string;
  updated_at?: string;
  message_count?: number;
  last_message_preview?: string;
}

export interface ChatListResponse {
  data: {
    chats: Chat[];
    total: number;
  };
  error: string | null;
}

export interface ChatResponse {
  data: {
    chat_id: string;
    created_at: string;
  };
  error: string | null;
}

export interface ChatDetailResponse {
  data: {
    chat_id: string;
    messages: Message[];
    created_at: string;
  };
  error: string | null;
}

export interface SendMessageRequest {
  message: string;
  stream?: boolean;
}

export interface SendMessageResponse {
  data: {
    chat_id: string;
    message_id: string;
    response?: string;
  };
  error: string | null;
}

export interface ChatState {
  chats: Chat[];
  currentChatId: string | null;
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
}
