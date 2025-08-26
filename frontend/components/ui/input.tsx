import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const inputVariants = cva(
  "flex w-full rounded-md border border-input bg-background px-3 py-2 ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200",
  {
    variants: {
      variant: {
        default: "bg-background",
        ghost:
          "bg-transparent border-transparent hover:border-input focus-visible:border-input",
        gradient:
          "bg-gradient-input-focus/20 focus-visible:bg-gradient-input-focus/40",
        filled: "bg-muted border-transparent focus-visible:bg-background",
      },
      size: {
        default: "h-10 text-sm",
        sm: "h-9 text-sm",
        lg: "h-11 text-base",
        "mobile-touch": "h-11 text-[16px]", // 44px height, 16px text to prevent iOS zoom
      },
      state: {
        default: "",
        error: "border-destructive focus-visible:ring-destructive",
        success: "border-success focus-visible:ring-success",
        warning: "border-warning focus-visible:ring-warning",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      state: "default",
    },
  },
);

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size">,
    VariantProps<typeof inputVariants> {
  /**
   * Icon to display on the left side of the input
   */
  leftIcon?: React.ReactNode;
  /**
   * Icon to display on the right side of the input
   */
  rightIcon?: React.ReactNode;
  /**
   * Loading state with spinner
   */
  loading?: boolean;
  /**
   * Error state for validation feedback
   */
  error?: boolean;
  /**
   * Success state for validation feedback
   */
  success?: boolean;
  /**
   * Warning state for validation feedback
   */
  warning?: boolean;
  /**
   * Helper text to display below the input
   */
  helperText?: string;
  /**
   * Label for the input (creates proper association)
   */
  label?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      variant,
      size,
      state,
      type = "text",
      leftIcon,
      rightIcon,
      loading = false,
      error = false,
      success = false,
      warning = false,
      helperText,
      label,
      id,
      ...props
    },
    ref,
  ) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;
    const helperId = `${inputId}-helper`;

    // Determine state based on props
    const currentState = error
      ? "error"
      : success
        ? "success"
        : warning
          ? "warning"
          : state;

    const inputElement = (
      <div className="relative">
        {leftIcon && (
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">
            {leftIcon}
          </div>
        )}
        <input
          type={type}
          className={cn(
            inputVariants({
              variant,
              size: size as
                | "default"
                | "sm"
                | "lg"
                | "mobile-touch"
                | null
                | undefined,
              state: currentState,
            }),
            leftIcon && "pl-10",
            (rightIcon || loading) && "pr-10",
            className,
          )}
          ref={ref}
          id={inputId}
          aria-invalid={error}
          aria-describedby={helperText ? helperId : undefined}
          disabled={loading || props.disabled}
          {...props}
        />
        {(rightIcon || loading) && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">
            {loading ? (
              <svg
                className="animate-spin h-4 w-4"
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
            ) : (
              rightIcon
            )}
          </div>
        )}
      </div>
    );

    if (label) {
      return (
        <div className="space-y-2">
          <label
            htmlFor={inputId}
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            {label}
          </label>
          {inputElement}
          {helperText && (
            <p
              id={helperId}
              className={cn(
                "text-xs",
                error && "text-destructive",
                success && "text-success",
                warning && "text-warning",
                !error && !success && !warning && "text-muted-foreground",
              )}
            >
              {helperText}
            </p>
          )}
        </div>
      );
    }

    return (
      <div className="space-y-1">
        {inputElement}
        {helperText && (
          <p
            id={helperId}
            className={cn(
              "text-xs",
              error && "text-destructive",
              success && "text-success",
              warning && "text-warning",
              !error && !success && !warning && "text-muted-foreground",
            )}
          >
            {helperText}
          </p>
        )}
      </div>
    );
  },
);
Input.displayName = "Input";

export { Input, inputVariants };
