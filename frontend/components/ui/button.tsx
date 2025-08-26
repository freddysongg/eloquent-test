import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 relative overflow-hidden",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow hover:bg-primary/90 active:scale-[0.98]",
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90 active:scale-[0.98]",
        outline:
          "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground active:scale-[0.98]",
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80 active:scale-[0.98]",
        ghost:
          "hover:bg-accent hover:text-accent-foreground active:scale-[0.98]",
        link: "text-primary underline-offset-4 hover:underline",
        // Enhanced gradient variants with better accessibility and mobile optimization
        "gradient-primary":
          "bg-gradient-primary text-primary-foreground shadow-lg hover:bg-gradient-primary-hover hover:shadow-xl transform hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 will-change-transform",
        "gradient-secondary":
          "bg-gradient-secondary text-secondary-foreground shadow-md hover:bg-gradient-secondary-hover transform hover:scale-[1.01] active:scale-[0.98] transition-all duration-200 will-change-transform",
        "gradient-accent":
          "bg-gradient-accent text-accent-foreground shadow-md hover:bg-gradient-accent-warm transform hover:scale-[1.01] active:scale-[0.98] transition-all duration-200 will-change-transform",
        "gradient-destructive":
          "bg-gradient-destructive text-destructive-foreground shadow-lg hover:bg-gradient-destructive-hover transform hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 will-change-transform",
        "gradient-subtle":
          "bg-gradient-primary-subtle text-foreground hover:bg-gradient-muted-subtle border border-border/50 transform hover:scale-[1.01] active:scale-[0.98] transition-all duration-200 will-change-transform",
        "gradient-glass":
          "glass-gradient text-foreground hover:bg-gradient-card-hover backdrop-blur-md transform hover:scale-[1.01] active:scale-[0.98] transition-all duration-200 will-change-transform",
      },
      size: {
        default: "h-10 px-4 py-2 min-w-[2.5rem]", // 40px height for mobile accessibility
        sm: "h-9 rounded-md px-3 text-xs min-w-[2.25rem]", // 36px minimum
        lg: "h-11 rounded-md px-8 min-w-[2.75rem]", // 44px for optimal mobile touch
        icon: "h-10 w-10 min-w-[2.5rem]", // 40px minimum touch target
        "icon-lg": "h-11 w-11 min-w-[2.75rem]", // 44px optimal touch target
        "mobile-touch": "h-11 px-6 min-w-[2.75rem]", // Mobile-optimized touch target
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  /**
   * Loading state with spinner
   */
  loading?: boolean;
  /**
   * Icon to display before text
   */
  leftIcon?: React.ReactNode;
  /**
   * Icon to display after text
   */
  rightIcon?: React.ReactNode;
  /**
   * Accessible label for screen readers when using icon-only buttons
   */
  "aria-label"?: string;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      "aria-label": ariaLabel,
      ...props
    },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";
    const isDisabled = disabled || loading;

    // When using asChild, we need to ensure only one child is passed to the Slot
    // The asChild pattern should not be used with leftIcon, rightIcon, or loading
    if (asChild && (leftIcon || rightIcon || loading)) {
      console.warn(
        "Button: leftIcon, rightIcon, and loading props are not supported when asChild is true. " +
          "These props will be ignored.",
      );
    }

    if (asChild) {
      return (
        <Comp
          className={cn(buttonVariants({ variant, size }), className)}
          ref={ref}
          {...props}
        >
          {children}
        </Comp>
      );
    }

    return (
      <Comp
        className={cn(
          buttonVariants({ variant, size }),
          loading && "cursor-not-allowed",
          className,
        )}
        ref={ref}
        disabled={isDisabled}
        aria-label={ariaLabel}
        aria-busy={loading}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="2"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        )}
        {!loading && leftIcon && (
          <span className="mr-2" aria-hidden="true">
            {leftIcon}
          </span>
        )}
        {children}
        {!loading && rightIcon && (
          <span className="ml-2" aria-hidden="true">
            {rightIcon}
          </span>
        )}
      </Comp>
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
