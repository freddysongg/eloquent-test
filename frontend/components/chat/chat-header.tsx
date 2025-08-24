'use client';

import { Button } from '@/components/ui/button';
import { PlusIcon } from 'lucide-react';
import { useUser } from '@clerk/nextjs';

interface ChatHeaderProps {
  user: ReturnType<typeof useUser>['user'];
  isConnected: boolean;
  onNewChat: () => void;
}

export function ChatHeader({ user, isConnected, onNewChat }: ChatHeaderProps) {
  return (
    <div className="border-b bg-background/80 backdrop-blur-sm px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-semibold">Eloquent AI</h1>
          <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
            isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={onNewChat}>
            <PlusIcon className="h-4 w-4 mr-2" />
            New Chat
          </Button>
          {user ? (
            <div className="text-sm text-muted-foreground">
              {user.firstName || user.emailAddresses[0]?.emailAddress}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              Anonymous User
            </div>
          )}
        </div>
      </div>
    </div>
  );
}