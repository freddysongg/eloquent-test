"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/utils";
import { Message } from "@/types/chat";
import { StreamingMessage } from "./typewriter-text";
import { MessageRenderer } from "./message-renderer";

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  className?: string;
}

export const MessageBubble = forwardRef<HTMLDivElement, MessageBubbleProps>(
  ({ message, isStreaming = false, className }, ref) => {
    const isUser = message.role === "user";
    const isAssistant = message.role === "assistant";

    return (
      <div
        ref={ref}
        className={cn(
          // Base styles following design guide - center-aligned like Claude
          "group relative w-full mb-6 animate-in fade-in-0 slide-in-from-bottom-2 duration-300",
          // Center container for all messages
          "flex justify-center",
          className,
        )}
      >
        {/* Message content bubble - centered with max width */}
        <div
          className={cn(
            // Base bubble styles with center alignment
            "relative rounded-lg px-4 py-3 text-[15px] leading-relaxed break-words",
            "transition-all duration-200 ease-out max-w-3xl w-full",
            // User message styling with gradient
            isUser && [
              "bg-gradient-message-user text-primary-foreground shadow-md",
              "hover:shadow-lg hover:scale-[1.01] transform-gpu",
              "border-0",
            ],
            // Assistant message styling with subtle gradient
            isAssistant && [
              "bg-gradient-message-ai border border-border/50 shadow-sm",
              "hover:bg-gradient-muted-subtle hover:border-border/70",
              "backdrop-blur-sm",
            ],
          )}
        >
          {/* Message content */}
          <div className="relative">
            {isStreaming && isAssistant ? (
              <StreamingMessage
                content={message.content}
                isStreaming={isStreaming}
              />
            ) : isAssistant ? (
              <MessageRenderer content={message.content} />
            ) : (
              <div className="text-[15px] leading-relaxed">
                {message.content}
              </div>
            )}
          </div>

          {/* Message timestamp */}
          <div
            className={cn(
              "absolute -bottom-5 text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200",
              "text-muted-foreground",
              "left-1/2 transform -translate-x-1/2",
            )}
          >
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        </div>
      </div>
    );
  },
);

MessageBubble.displayName = "MessageBubble";
