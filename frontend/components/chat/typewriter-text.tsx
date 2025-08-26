"use client";

import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface TypewriterTextProps {
  text: string;
  speed?: number;
  showCursor?: boolean;
  onComplete?: () => void;
  className?: string;
}

export function TypewriterText({
  text,
  speed = 15, // Faster default speed for smoother animation
  showCursor = true,
  onComplete,
  className,
}: TypewriterTextProps) {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (currentIndex < text.length) {
      timeoutRef.current = setTimeout(() => {
        // Add multiple characters at once for very fast typing
        const charsToAdd = Math.min(1, text.length - currentIndex);
        setDisplayedText(text.slice(0, currentIndex + charsToAdd));
        setCurrentIndex(currentIndex + charsToAdd);
      }, speed);
    } else if (!isComplete) {
      setIsComplete(true);
      onComplete?.();
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [currentIndex, text, speed, isComplete, onComplete]);

  // Reset when text changes
  useEffect(() => {
    setDisplayedText("");
    setCurrentIndex(0);
    setIsComplete(false);
  }, [text]);

  return (
    <span className={cn("relative", className)}>
      {displayedText}
      {showCursor && !isComplete && (
        <span className="inline-block w-0.5 h-5 ml-0.5 bg-current animate-pulse opacity-75" />
      )}
    </span>
  );
}

interface StreamingMessageProps {
  content: string;
  isStreaming: boolean;
  onStreamComplete?: () => void;
  className?: string;
}

export function StreamingMessage({
  content,
  isStreaming,
  onStreamComplete,
  className,
}: StreamingMessageProps) {
  if (isStreaming && content) {
    const typewriterProps: TypewriterTextProps = {
      text: content,
      speed: 10, // Very fast typing for streaming responses
      showCursor: true,
    };

    if (className) {
      typewriterProps.className = className;
    }

    if (onStreamComplete) {
      typewriterProps.onComplete = onStreamComplete;
    }

    return (
      <div className="prose prose-sm max-w-none">
        <TypewriterText {...typewriterProps} />
      </div>
    );
  }

  return (
    <div className={cn("prose prose-sm max-w-none", className)}>
      {content}
      {isStreaming && (
        <span className="inline-block ml-1 w-0.5 h-5 bg-current animate-pulse opacity-75" />
      )}
    </div>
  );
}
