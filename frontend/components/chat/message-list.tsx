'use client';

import { LoadingSpinner } from '@/components/ui/loading-spinner';

// TODO: Import actual message types when created
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-2">Welcome to Eloquent AI</h2>
          <p className="text-muted-foreground mb-4">
            Your intelligent fintech FAQ assistant. Ask me anything about financial services!
          </p>
          <div className="text-sm text-muted-foreground">
            Examples: &quot;How do I open an account?&quot;, &quot;What are your transaction fees?&quot;, &quot;How secure is my data?&quot;
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-3xl rounded-lg px-4 py-2 ${
              message.role === 'user'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted'
            }`}
          >
            {message.content}
          </div>
        </div>
      ))}
      
      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-muted rounded-lg px-4 py-2">
            <LoadingSpinner size="sm" />
          </div>
        </div>
      )}
    </div>
  );
}