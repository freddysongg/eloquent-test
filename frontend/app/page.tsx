import { Suspense } from 'react';
import { ChatInterface } from '@/components/chat/chat-interface';
import { ChatSidebar } from '@/components/chat/chat-sidebar';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

export default function HomePage() {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <div className="hidden md:flex md:w-64 md:flex-col">
        <Suspense fallback={<div className="flex items-center justify-center h-full"><LoadingSpinner /></div>}>
          <ChatSidebar />
        </Suspense>
      </div>

      {/* Main chat interface */}
      <div className="flex-1 flex flex-col">
        <Suspense fallback={<div className="flex items-center justify-center h-full"><LoadingSpinner /></div>}>
          <ChatInterface />
        </Suspense>
      </div>
    </div>
  );
}