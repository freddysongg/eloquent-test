'use client';

export function ChatSidebar() {
  return (
    <div className="border-r bg-card h-full p-4">
      <div className="space-y-4">
        <div className="font-semibold">Chat History</div>
        <div className="text-sm text-muted-foreground">
          No previous chats
          <br />
          (Implementation coming with Integration Agent)
        </div>
      </div>
    </div>
  );
}