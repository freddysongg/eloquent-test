"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const loadingSpinnerVariants = cva("animate-spin", {
  variants: {
    variant: {
      default: "text-primary",
      gradient: "text-transparent bg-gradient-primary bg-clip-text",
      muted: "text-muted-foreground",
      destructive: "text-destructive",
      accent: "text-accent-foreground",
    },
    size: {
      xs: "w-3 h-3",
      sm: "w-4 h-4",
      md: "w-6 h-6",
      lg: "w-8 h-8",
      xl: "w-12 h-12",
    },
    speed: {
      slow: "animate-[spin_2s_linear_infinite]",
      normal: "animate-spin",
      fast: "animate-[spin_0.5s_linear_infinite]",
    },
  },
  defaultVariants: {
    variant: "default",
    size: "md",
    speed: "normal",
  },
});

export interface LoadingSpinnerProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof loadingSpinnerVariants> {
  /**
   * Loading text to display below spinner
   */
  text?: string;
  /**
   * Whether to show the spinner inline or as a block element
   */
  inline?: boolean;
  /**
   * Custom spinner type
   */
  type?: "spinner" | "dots" | "pulse" | "bars";
  /**
   * Accessible label for screen readers
   */
  "aria-label"?: string;
}

const DotsSpinner = ({
  size,
  variant,
}: {
  size?: string | undefined;
  variant?: string | undefined;
}) => {
  const dotSize =
    size === "xs"
      ? "w-1 h-1"
      : size === "sm"
        ? "w-1.5 h-1.5"
        : size === "lg"
          ? "w-2.5 h-2.5"
          : size === "xl"
            ? "w-3 h-3"
            : "w-2 h-2";
  const colorClass =
    variant === "gradient"
      ? "bg-gradient-primary"
      : variant === "muted"
        ? "bg-muted-foreground"
        : variant === "destructive"
          ? "bg-destructive"
          : "bg-primary";

  return (
    <div className="flex space-x-1">
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className={cn(dotSize, colorClass, "rounded-full animate-pulse")}
          style={{
            animationDelay: `${index * 0.2}s`,
            animationDuration: "1.4s",
          }}
        />
      ))}
    </div>
  );
};

const PulseSpinner = ({
  size,
  variant,
}: {
  size?: string | undefined;
  variant?: string | undefined;
}) => {
  const pulseSize =
    size === "xs"
      ? "w-3 h-3"
      : size === "sm"
        ? "w-4 h-4"
        : size === "lg"
          ? "w-8 h-8"
          : size === "xl"
            ? "w-12 h-12"
            : "w-6 h-6";
  const colorClass =
    variant === "gradient"
      ? "bg-gradient-primary"
      : variant === "muted"
        ? "bg-muted-foreground/50"
        : variant === "destructive"
          ? "bg-destructive/50"
          : "bg-primary/50";

  return (
    <div className={cn(pulseSize, colorClass, "rounded-full animate-pulse")} />
  );
};

const BarsSpinner = ({
  size,
  variant,
}: {
  size?: string | undefined;
  variant?: string | undefined;
}) => {
  const barHeight =
    size === "xs"
      ? "h-2"
      : size === "sm"
        ? "h-3"
        : size === "lg"
          ? "h-6"
          : size === "xl"
            ? "h-8"
            : "h-4";
  const colorClass =
    variant === "gradient"
      ? "bg-gradient-primary"
      : variant === "muted"
        ? "bg-muted-foreground"
        : variant === "destructive"
          ? "bg-destructive"
          : "bg-primary";

  return (
    <div className="flex items-end space-x-1">
      {[0, 1, 2, 3].map((index) => (
        <div
          key={index}
          className={cn("w-1", barHeight, colorClass, "animate-pulse")}
          style={{
            animationDelay: `${index * 0.1}s`,
            animationDuration: "0.8s",
          }}
        />
      ))}
    </div>
  );
};

export const LoadingSpinner = React.forwardRef<
  HTMLDivElement,
  LoadingSpinnerProps
>(
  (
    {
      className,
      variant,
      size,
      speed = "normal",
      text,
      inline = false,
      type = "spinner",
      "aria-label": ariaLabel,
      ...props
    },
    ref,
  ) => {
    const containerClass = inline
      ? "inline-flex items-center gap-2"
      : "flex flex-col items-center gap-2";

    const renderSpinner = () => {
      switch (type) {
        case "dots":
          return (
            <DotsSpinner
              size={size ?? undefined}
              variant={variant ?? undefined}
            />
          );
        case "pulse":
          return (
            <PulseSpinner
              size={size ?? undefined}
              variant={variant ?? undefined}
            />
          );
        case "bars":
          return (
            <BarsSpinner
              size={size ?? undefined}
              variant={variant ?? undefined}
            />
          );
        case "spinner":
        default:
          return (
            <svg
              className={cn(loadingSpinnerVariants({ variant, size, speed }))}
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden={!ariaLabel}
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="2"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          );
      }
    };

    return (
      <div
        ref={ref}
        className={cn(containerClass, className)}
        role="status"
        aria-label={ariaLabel || "Loading"}
        {...props}
      >
        {renderSpinner()}
        {text && (
          <p
            className={cn(
              "text-sm animate-pulse",
              variant === "muted" ? "text-muted-foreground" : "text-foreground",
            )}
          >
            {text}
          </p>
        )}
        <span className="sr-only">{ariaLabel || "Loading..."}</span>
      </div>
    );
  },
);
LoadingSpinner.displayName = "LoadingSpinner";

export { loadingSpinnerVariants };
