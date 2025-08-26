"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { Message } from "@/types/chat";
import { MessageBubble } from "./message-bubble";
import { ThinkingIndicator } from "./thinking-indicator";

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  className?: string;
}

export function MessageList({
  messages,
  isLoading,
  isStreaming,
  className,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);

  // Auto-scroll to bottom when new messages arrive or streaming
  useEffect(() => {
    if (isNearBottom && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, isStreaming, isNearBottom]);

  // Track if user is near bottom for smart auto-scrolling
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const nearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setIsNearBottom(nearBottom);
      setShowScrollToBottom(!nearBottom && messages.length > 0);
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, [messages.length]);

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Empty state
  if (messages.length === 0 && !isLoading && !isStreaming) {
    return (
      <div
        className={cn("flex-1 flex items-center justify-center p-6", className)}
      >
        <div className="text-center max-w-2xl mx-auto">
          <div className="mb-8 relative">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-primary-subtle flex items-center justify-center">
              <div className="w-8 h-8 rounded-full bg-gradient-primary opacity-20" />
            </div>
            <h2 className="text-2xl font-semibold mb-3 text-gradient-primary">
              Welcome to Eloquent AI
            </h2>
            <p className="text-muted-foreground mb-6 leading-relaxed">
              Your intelligent fintech FAQ assistant. Ask me anything about
              financial services, account management, or security!
            </p>
          </div>

          {/* Example questions */}
          <div className="grid gap-3 text-left">
            <div className="text-sm font-medium text-muted-foreground mb-2">
              Try asking:
            </div>
            {[
              "How do I open an account?",
              "What are your transaction fees?",
              "How secure is my data?",
              "Tell me about your mobile app features",
            ].map((example, index) => (
              <div
                key={index}
                className="p-3 rounded-lg bg-gradient-card-hover border border-border/50 text-sm hover:shadow-sm transition-all duration-200 cursor-default"
              >
                &quot;{example}&quot;
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex-1 relative", className)}>
      {/* Messages container with optimized scrolling */}
      <div
        ref={containerRef}
        className={cn(
          "h-full overflow-y-auto px-4 md:px-6 py-6",
          // Custom scrollbar styling
          "scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent",
          // Smooth scrolling
          "scroll-smooth",
        )}
        style={{
          scrollbarGutter: "stable",
        }}
      >
        <div className="max-w-5xl mx-auto space-y-1 px-4">
          {messages.map((message, index) => {
            const isLastAssistantMessage =
              message.role === "assistant" &&
              index === messages.length - 1 &&
              isStreaming;

            return (
              <MessageBubble
                key={message.id}
                message={message}
                isStreaming={isLastAssistantMessage}
              />
            );
          })}

          {/* Thinking indicator when loading */}
          {isLoading && <ThinkingIndicator />}

          {/* Bottom spacer for smooth scrolling */}
          <div ref={bottomRef} className="h-4" />
        </div>
      </div>

      {/* Scroll to bottom button */}
      {showScrollToBottom && (
        <button
          onClick={scrollToBottom}
          className={cn(
            "absolute bottom-4 right-4 z-10",
            "w-10 h-10 rounded-full shadow-lg",
            "bg-gradient-primary text-primary-foreground",
            "hover:bg-gradient-primary-hover hover:shadow-xl",
            "transform hover:scale-105 transition-all duration-200",
            "flex items-center justify-center",
            "animate-in slide-in-from-bottom-2 fade-in-0",
          )}
          aria-label="Scroll to bottom"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 14l-7 7m0 0l-7-7m7 7V3"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
