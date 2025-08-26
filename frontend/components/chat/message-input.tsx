"use client";

import { useState, useRef, useEffect, KeyboardEvent, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SendIcon, StopCircleIcon, PaperclipIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { TypingIndicator } from "./thinking-indicator";

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  onStop?: () => void;
  className?: string;
}

export function MessageInput({
  onSendMessage,
  disabled = false,
  placeholder,
  maxLength = 2000,
  onStop,
  className,
}: MessageInputProps) {
  const [message, setMessage] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on content
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const scrollHeight = Math.min(textarea.scrollHeight, 200); // Max height ~8 lines
      textarea.style.height = `${scrollHeight}px`;
    }
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [message, adjustHeight]);

  const handleSend = useCallback(() => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !disabled) {
      onSendMessage(trimmedMessage);
      setMessage("");
      // Reset height after clearing
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  }, [message, disabled, onSendMessage]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter") {
      if (e.shiftKey) {
        // Allow new line with Shift+Enter
        return;
      } else {
        // Send message with Enter
        e.preventDefault();
        handleSend();
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= maxLength) {
      setMessage(value);
    }
  };

  const isAtLimit = message.length >= maxLength;
  const canSend = message.trim().length > 0 && !disabled;

  return (
    <div
      className={cn(
        "border-t border-border/50 bg-background/85 backdrop-blur-md px-4 md:px-6 py-4 safe-bottom",
        "transition-all duration-300 ease-out",
        "shadow-sm",
        isFocused && [
          "border-primary/30 shadow-md",
          "bg-gradient-background-subtle/90",
        ],
        className,
      )}
    >
      <div className="w-full max-w-6xl mx-auto">
        {/* Typing indicator when disabled */}
        {disabled && (
          <div className="mb-3">
            <TypingIndicator />
          </div>
        )}

        {/* Input container */}
        <div
          className={cn(
            "relative rounded-xl transition-all duration-200",
            "border border-input bg-background backdrop-blur-sm",
            "focus-within:border-primary/50 focus-within:shadow-md",
            "hover:border-primary/30 hover:shadow-sm",
            isFocused && "ring-2 ring-primary/20 shadow-lg border-primary/50",
          )}
        >
          <div className="flex items-end gap-2 p-2">
            {/* Future: Attachment button */}
            <button
              className={cn(
                "flex items-center justify-center rounded-lg",
                "text-muted-foreground/60 hover:text-muted-foreground/80",
                "transition-all duration-200 flex-shrink-0",
                "opacity-50 cursor-not-allowed",
                "hover:bg-muted/20 self-end",
                "w-10 h-10 mb-1",
              )}
              disabled
              title="File attachments (coming soon)"
            >
              <PaperclipIcon className="w-4 h-4" />
            </button>

            {/* Textarea - fixed to take full available width */}
            <div className="flex-1 min-w-0">
              <Textarea
                ref={textareaRef}
                value={message}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder={placeholder || "Message Eloquent AI..."}
                disabled={disabled}
                variant="ghost"
                size="mobile-optimized"
                autoResize
                maxHeight={200}
                className={cn(
                  "border-0 bg-transparent resize-none w-full text-foreground",
                  "focus:ring-0 focus-visible:ring-0 focus-visible:ring-offset-0",
                  "focus:bg-transparent hover:bg-transparent",
                  "placeholder:text-muted-foreground/60 text-[15px] leading-[1.5]",
                  "py-3 px-3 min-h-[44px]",
                  "transition-colors duration-200",
                  disabled && "opacity-60 cursor-not-allowed",
                )}
                style={{
                  height: "auto",
                }}
              />
            </div>

            {/* Send/Stop button */}
            {disabled && onStop ? (
              <Button
                onClick={onStop}
                variant="outline"
                size="icon-lg"
                className={cn(
                  "rounded-xl hover:bg-destructive/10 hover:border-destructive/30",
                  "transition-all duration-200 shadow-sm w-11 h-11",
                  "flex-shrink-0 self-end mb-1",
                )}
                title="Stop generating"
                aria-label="Stop generating response"
              >
                <StopCircleIcon className="h-5 w-5 text-destructive" />
              </Button>
            ) : (
              <Button
                onClick={handleSend}
                disabled={!canSend}
                variant={canSend ? "gradient-primary" : "ghost"}
                size="icon-lg"
                className={cn(
                  "rounded-xl mobile-touch-target transition-all duration-200",
                  "w-11 h-11 flex-shrink-0 self-end mb-1",
                  canSend
                    ? [
                        "shadow-md hover:shadow-lg transform hover:scale-105",
                        "bg-gradient-primary hover:bg-gradient-primary-hover",
                        "will-change-transform",
                      ]
                    : [
                        "opacity-40 cursor-not-allowed",
                        "hover:opacity-40 hover:bg-transparent",
                      ],
                )}
                title={canSend ? "Send message" : "Type a message to send"}
                aria-label={canSend ? "Send message" : "Type a message to send"}
              >
                <SendIcon className="h-5 w-5" />
              </Button>
            )}
          </div>

          {/* Character count and keyboard shortcut hint */}
          <div className="flex items-center justify-between px-4 pb-3 pt-1">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground/80 hidden sm:inline">
                Press Enter to send, Shift + Enter for new line
              </span>
              <span className="text-xs text-muted-foreground/80 sm:hidden">
                Enter to send
              </span>
            </div>
            <div
              className={cn(
                "text-xs font-medium transition-colors duration-200",
                isAtLimit ? "text-destructive" : "text-muted-foreground/80",
                message.length > maxLength * 0.8 &&
                  !isAtLimit &&
                  "text-warning",
              )}
            >
              {message.length}/{maxLength}
            </div>
          </div>
        </div>

        {/* Mobile keyboard spacing and visual padding */}
        <div className="h-6 sm:h-4" />
      </div>
    </div>
  );
}
