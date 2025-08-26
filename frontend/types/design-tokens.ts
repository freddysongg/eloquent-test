/**
 * Enhanced Design Token Types
 * Provides TypeScript support for the semantic design token system
 */

// Color Token Types
export type ColorToken =
  | "background"
  | "foreground"
  | "card"
  | "card-foreground"
  | "popover"
  | "popover-foreground"
  | "primary"
  | "primary-foreground"
  | "secondary"
  | "secondary-foreground"
  | "muted"
  | "muted-foreground"
  | "accent"
  | "accent-foreground"
  | "destructive"
  | "destructive-foreground"
  | "border"
  | "input"
  | "ring";

// Semantic Color Extensions
export type SemanticColorToken =
  | "success"
  | "success-foreground"
  | "warning"
  | "warning-foreground"
  | "info"
  | "info-foreground";

// Surface Color Tokens
export type SurfaceColorToken =
  | "surface-elevated"
  | "surface-hover"
  | "surface-pressed"
  | "surface-disabled";

// Interactive Color Tokens
export type InteractiveColorToken =
  | "interactive-default"
  | "interactive-hover"
  | "interactive-pressed"
  | "interactive-disabled";

// Text Color Tokens
export type TextColorToken =
  | "text-primary"
  | "text-secondary"
  | "text-tertiary"
  | "text-disabled"
  | "text-inverse";

// Border Color Tokens
export type BorderColorToken =
  | "border-primary"
  | "border-secondary"
  | "border-hover"
  | "border-focus"
  | "border-disabled";

// All Color Tokens
export type AllColorTokens =
  | ColorToken
  | SemanticColorToken
  | SurfaceColorToken
  | InteractiveColorToken
  | TextColorToken
  | BorderColorToken;

// Spacing Tokens
export type SpacingToken =
  | "space-xs" // 4px
  | "space-sm" // 8px
  | "space-md" // 16px
  | "space-lg" // 24px
  | "space-xl" // 32px
  | "space-2xl"; // 48px

// Typography Tokens
export type FontSizeToken =
  | "font-size-xs" // 12px
  | "font-size-sm" // 14px
  | "font-size-base" // 16px
  | "font-size-lg" // 18px
  | "font-size-xl" // 20px
  | "font-size-2xl"; // 24px

export type LineHeightToken =
  | "line-height-tight" // 1.25
  | "line-height-normal" // 1.5
  | "line-height-relaxed" // 1.625
  | "line-height-loose"; // 2.0

// Animation Tokens
export type DurationToken =
  | "duration-instant" // 50ms
  | "duration-fast" // 150ms
  | "duration-normal" // 250ms
  | "duration-slow" // 350ms
  | "duration-slower"; // 500ms

export type EasingToken =
  | "ease-linear"
  | "ease-in"
  | "ease-out"
  | "ease-in-out"
  | "ease-bounce";

// Shadow Tokens
export type ShadowToken = "shadow-sm" | "shadow-md" | "shadow-lg" | "shadow-xl";

// Component Variant Types
export type ButtonVariant =
  | "default"
  | "destructive"
  | "outline"
  | "secondary"
  | "ghost"
  | "link"
  | "gradient-primary"
  | "gradient-secondary"
  | "gradient-accent"
  | "gradient-destructive"
  | "gradient-subtle"
  | "gradient-glass";

export type ButtonSize =
  | "default"
  | "sm"
  | "lg"
  | "icon"
  | "icon-lg"
  | "mobile-touch";

export type CardVariant =
  | "default"
  | "gradient"
  | "gradient-subtle"
  | "gradient-glass"
  | "gradient-message"
  | "gradient-interactive"
  | "gradient-elevated";

export type CardSize = "default" | "sm" | "lg" | "compact" | "mobile-touch";

export type InputVariant = "default" | "ghost" | "gradient" | "filled";

export type InputSize = "default" | "sm" | "lg" | "mobile-touch";

export type InputState = "default" | "error" | "success" | "warning";

export type TextareaVariant = "default" | "ghost" | "gradient";

export type TextareaSize = "default" | "sm" | "lg" | "mobile-optimized";

export type AlertVariant =
  | "default"
  | "destructive"
  | "warning"
  | "success"
  | "info"
  | "gradient-destructive"
  | "gradient-warning"
  | "gradient-success"
  | "gradient-info";

export type AlertSize = "default" | "sm" | "lg";

export type LoadingSpinnerVariant =
  | "default"
  | "gradient"
  | "muted"
  | "destructive"
  | "accent";

export type LoadingSpinnerSize = "xs" | "sm" | "md" | "lg" | "xl";

export type LoadingSpinnerType = "spinner" | "dots" | "pulse" | "bars";

export type LoadingSpinnerSpeed = "slow" | "normal" | "fast";

export type TooltipVariant =
  | "default"
  | "secondary"
  | "gradient"
  | "gradient-glass"
  | "destructive"
  | "success"
  | "warning"
  | "info";

export type TooltipSize = "sm" | "default" | "lg";

export type NavigationVariant = "default" | "gradient" | "glass" | "floating";

export type NavigationSize = "default" | "sm" | "lg" | "mobile-touch";

export type NavigationItemVariant = "default" | "ghost" | "gradient" | "active";

// Utility Types
export type ComponentVariants<T> = {
  [K in keyof T]: T[K] extends string ? T[K] : never;
};

// Design Token Utility Functions
export interface DesignTokens {
  colors: Record<AllColorTokens, string>;
  spacing: Record<SpacingToken, string>;
  typography: {
    fontSize: Record<FontSizeToken, string>;
    lineHeight: Record<LineHeightToken, string>;
  };
  animation: {
    duration: Record<DurationToken, string>;
    easing: Record<EasingToken, string>;
  };
  shadows: Record<ShadowToken, string>;
}

// CSS Custom Property Helper
export type CSSCustomProperty<T extends string> = `var(--${T})`;

// Helper type for getting CSS custom property
export type GetToken<T extends AllColorTokens | SpacingToken | ShadowToken> =
  CSSCustomProperty<T>;

// Component Props Helper Types
export interface AccessibilityProps {
  "aria-label"?: string;
  "aria-labelledby"?: string;
  "aria-describedby"?: string;
  role?: string;
}

export interface InteractiveProps {
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  onFocus?: () => void;
  onBlur?: () => void;
}

export interface ValidationProps {
  error?: boolean;
  success?: boolean;
  warning?: boolean;
  helperText?: string;
}

// Mobile Optimization Types
export interface MobileOptimizedProps {
  /**
   * Whether the component should use mobile-optimized sizing
   */
  mobileOptimized?: boolean;
  /**
   * Whether the component should meet 44px touch target minimum
   */
  touchTarget?: boolean;
}

// Performance Types
export interface PerformanceProps {
  /**
   * Whether to use GPU acceleration for animations
   */
  gpuAccelerated?: boolean;
  /**
   * Whether to respect user's reduced motion preference
   */
  respectReducedMotion?: boolean;
}

// Theme Types
export interface ThemeAwareProps {
  /**
   * Whether the component adapts to light/dark theme
   */
  themeAware?: boolean;
  /**
   * Whether the component supports high contrast mode
   */
  highContrast?: boolean;
}

// Combined Component Props
export interface EnhancedComponentProps
  extends AccessibilityProps,
    InteractiveProps,
    ValidationProps,
    MobileOptimizedProps,
    PerformanceProps,
    ThemeAwareProps {
  className?: string;
  children?: React.ReactNode;
}

// Export commonly used combinations
export type StandardComponentProps = Pick<
  EnhancedComponentProps,
  "className" | "children" | "aria-label" | "disabled"
>;

export type FormComponentProps = Pick<
  EnhancedComponentProps,
  | "className"
  | "disabled"
  | "error"
  | "success"
  | "warning"
  | "helperText"
  | "aria-label"
>;

export type InteractiveComponentProps = Pick<
  EnhancedComponentProps,
  | "className"
  | "children"
  | "disabled"
  | "loading"
  | "onClick"
  | "aria-label"
  | "touchTarget"
>;
