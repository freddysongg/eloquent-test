import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const textareaVariants = cva(
  "flex w-full rounded-md border border-input bg-transparent px-3 py-2 shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200 resize-none",
  {
    variants: {
      variant: {
        default: "bg-background",
        ghost:
          "bg-transparent border-transparent hover:border-input focus-visible:border-input",
        gradient:
          "bg-gradient-input-focus/20 focus-visible:bg-gradient-input-focus/40",
      },
      size: {
        default: "min-h-[60px] text-sm",
        sm: "min-h-[48px] text-sm",
        lg: "min-h-[80px] text-base",
        "mobile-optimized": "min-h-[44px] text-[16px] leading-5", // Prevents zoom on iOS
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    VariantProps<typeof textareaVariants> {
  /**
   * Whether the textarea should auto-resize based on content
   */
  autoResize?: boolean;
  /**
   * Maximum height for auto-resize (in px)
   */
  maxHeight?: number;
  /**
   * Error state for validation feedback
   */
  error?: boolean;
  /**
   * Helper text to display below the textarea
   */
  helperText?: string;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      variant,
      size,
      autoResize = false,
      maxHeight = 200,
      error = false,
      helperText,
      onChange,
      ...props
    },
    ref,
  ) => {
    const textareaRef = React.useRef<HTMLTextAreaElement>(null);

    // Use useImperativeHandle to properly forward the ref
    React.useImperativeHandle(ref, () => textareaRef.current!, []);

    const adjustHeight = React.useCallback(() => {
      const textarea = textareaRef.current;
      if (textarea && autoResize) {
        textarea.style.height = "auto";
        const scrollHeight = Math.min(textarea.scrollHeight, maxHeight);
        textarea.style.height = `${scrollHeight}px`;
      }
    }, [autoResize, maxHeight]);

    React.useEffect(() => {
      adjustHeight();
    }, [adjustHeight]);

    const handleChange = React.useCallback(
      (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        onChange?.(e);
        adjustHeight();
      },
      [onChange, adjustHeight],
    );

    return (
      <div className="space-y-1">
        <textarea
          className={cn(
            textareaVariants({ variant, size }),
            error && "border-destructive focus-visible:ring-destructive",
            className,
          )}
          ref={textareaRef}
          onChange={handleChange}
          aria-invalid={error}
          aria-describedby={
            helperText ? `${props.id || "textarea"}-helper` : undefined
          }
          {...props}
        />
        {helperText && (
          <p
            id={`${props.id || "textarea"}-helper`}
            className={cn(
              "text-xs",
              error ? "text-destructive" : "text-muted-foreground",
            )}
          >
            {helperText}
          </p>
        )}
      </div>
    );
  },
);
Textarea.displayName = "Textarea";

export { Textarea, textareaVariants };
