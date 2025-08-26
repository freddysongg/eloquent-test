"use client";

import { cn } from "@/lib/utils";

interface ThinkingIndicatorProps {
  message?: string;
  className?: string;
}

export function ThinkingIndicator({
  message,
  className,
}: ThinkingIndicatorProps) {
  return (
    <div
      className={cn(
        "w-full mb-6 animate-in fade-in-0 slide-in-from-bottom-2 duration-300",
        // Center container like Claude
        "flex justify-center",
        className,
      )}
    >
      {/* Thinking bubble following design guide */}
      <div className="relative rounded-lg px-4 py-3 bg-gradient-message-ai border border-border/50 shadow-sm backdrop-blur-sm max-w-3xl w-full">
        <div className="flex items-center justify-center">
          {/* Claude-style animated thinking dots - only dots, no text */}
          <div className="flex gap-1.5">
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className={cn(
                  "w-2 h-2 rounded-full bg-muted-foreground/80",
                  "animate-pulse",
                )}
                style={{
                  animationDelay: `${index * 0.4}s`,
                  animationDuration: "1.2s",
                  animation: `fade-in-out 1.2s ease-in-out infinite ${index * 0.4}s`,
                }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* CSS for custom fade-in-out animation */}
      <style jsx>{`
        @keyframes fade-in-out {
          0%,
          60%,
          100% {
            opacity: 0.3;
          }
          30% {
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}

export function TypingIndicator({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm text-muted-foreground",
        className,
      )}
    >
      <div className="flex gap-1">
        {[0, 1, 2].map((index) => (
          <div
            key={index}
            className={cn(
              "w-1.5 h-1.5 rounded-full bg-muted-foreground/50",
              "animate-bounce",
            )}
            style={{
              animationDelay: `${index * 0.1}s`,
              animationDuration: "0.8s",
            }}
          />
        ))}
      </div>
      <span className="animate-pulse">AI is responding...</span>
    </div>
  );
}
