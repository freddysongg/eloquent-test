import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const cardVariants = cva(
  "rounded-xl border text-card-foreground shadow transition-all duration-200 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background will-change-transform",
  {
    variants: {
      variant: {
        default: "bg-card hover:shadow-md",
        gradient:
          "bg-gradient-card hover:bg-gradient-card-hover hover:shadow-lg transform hover:scale-[1.01]",
        "gradient-subtle":
          "bg-gradient-muted-subtle hover:shadow-md transform hover:scale-[1.005]",
        "gradient-glass":
          "glass-gradient backdrop-blur-md border-border/30 hover:bg-gradient-card-hover/20 transform hover:scale-[1.005]",
        "gradient-message":
          "bg-gradient-message-ai hover:bg-gradient-message-ai/80",
        "gradient-interactive":
          "bg-gradient-card hover:bg-gradient-card-hover cursor-pointer transform hover:scale-[1.02] active:scale-[0.98] transition-transform duration-150",
        "gradient-elevated":
          "bg-gradient-background-subtle shadow-lg hover:shadow-xl transform hover:scale-[1.01] border-border/20",
      },
      size: {
        default: "p-6",
        sm: "p-4",
        lg: "p-8",
        compact: "p-3",
        "mobile-touch": "p-4 min-h-[44px]", // Mobile-optimized touch target
      },
      interactive: {
        true: "cursor-pointer hover:shadow-lg focus:shadow-lg transition-shadow duration-200",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      interactive: false,
    },
  },
);

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  /**
   * Whether the card should be focusable and interactive
   */
  interactive?: boolean;
  /**
   * Loading state for the card content
   */
  loading?: boolean;
  /**
   * Accessible role for semantic meaning
   */
  role?: string;
  /**
   * ARIA label for screen readers
   */
  "aria-label"?: string;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant,
      size,
      interactive,
      loading,
      role = "article",
      "aria-label": ariaLabel,
      children,
      ...props
    },
    ref,
  ) => {
    const cardClassName = cn(
      cardVariants({ variant, size, interactive }),
      loading && "animate-pulse cursor-wait",
      className,
    );

    return (
      <div
        ref={ref}
        className={cardClassName}
        role={interactive ? "button" : role}
        tabIndex={interactive ? 0 : undefined}
        aria-label={ariaLabel}
        aria-busy={loading}
        {...props}
      >
        {loading ? (
          <div className="space-y-2">
            <div className="h-4 bg-muted-foreground/20 rounded animate-pulse" />
            <div className="h-4 bg-muted-foreground/20 rounded animate-pulse w-3/4" />
            <div className="h-4 bg-muted-foreground/20 rounded animate-pulse w-1/2" />
          </div>
        ) : (
          children
        )}
      </div>
    );
  },
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6 pb-3", className)}
    role="banner"
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "font-semibold leading-none tracking-tight text-lg",
      className,
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground leading-relaxed", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} role="main" {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex items-center justify-between p-6 pt-0 gap-2",
      className,
    )}
    role="contentinfo"
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
};
