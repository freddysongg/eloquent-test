import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const navigationVariants = cva(
  "flex items-center justify-between w-full transition-all duration-200",
  {
    variants: {
      variant: {
        default: "bg-background border-b border-border",
        gradient: "bg-gradient-background-subtle border-b border-border/50",
        glass: "glass-gradient backdrop-blur-md border-b border-border/30",
        floating:
          "bg-background/95 backdrop-blur-md rounded-xl border border-border/50 shadow-lg mx-4 mt-4",
      },
      size: {
        default: "h-14 px-4",
        sm: "h-12 px-3",
        lg: "h-16 px-6",
        "mobile-touch": "h-14 px-4 min-h-[56px]", // Optimal mobile touch target
      },
      sticky: {
        true: "sticky top-0 z-50",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      sticky: false,
    },
  },
);

const navigationItemVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent/50 hover:text-accent-foreground",
        gradient: "hover:bg-gradient-primary-subtle text-foreground",
        active: "bg-gradient-primary text-primary-foreground shadow-md",
      },
      size: {
        default: "h-9 px-3 py-2",
        sm: "h-8 px-2 py-1 text-xs",
        lg: "h-10 px-4 py-2",
        "mobile-touch": "h-11 px-4 py-2 min-w-[44px]", // 44px minimum touch target
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface NavigationProps
  extends React.HTMLAttributes<HTMLElement>,
    VariantProps<typeof navigationVariants> {
  /**
   * Logo or brand element
   */
  logo?: React.ReactNode;
  /**
   * Navigation items (usually NavItem components)
   */
  children?: React.ReactNode;
  /**
   * Actions for the right side (user menu, settings, etc.)
   */
  actions?: React.ReactNode;
  /**
   * Mobile menu toggle for responsive navigation
   */
  mobileMenuOpen?: boolean;
  /**
   * Callback for mobile menu toggle
   */
  onMobileMenuToggle?: () => void;
  /**
   * Whether to show mobile menu toggle button
   */
  showMobileToggle?: boolean;
}

export interface NavigationItemProps
  extends React.AnchorHTMLAttributes<HTMLAnchorElement>,
    VariantProps<typeof navigationItemVariants> {
  /**
   * Whether this navigation item is currently active
   */
  active?: boolean;
  /**
   * Icon to display before the text
   */
  icon?: React.ReactNode;
  /**
   * Whether to render as a button instead of link
   */
  asButton?: boolean;
  /**
   * Click handler for button variant
   */
  onClick?: () => void;
}

const Navigation = React.forwardRef<HTMLElement, NavigationProps>(
  (
    {
      className,
      variant,
      size,
      sticky,
      logo,
      children,
      actions,
      mobileMenuOpen = false,
      onMobileMenuToggle,
      showMobileToggle = false,
      ...props
    },
    ref,
  ) => {
    return (
      <nav
        ref={ref}
        className={cn(navigationVariants({ variant, size, sticky }), className)}
        role="navigation"
        aria-label="Main navigation"
        {...props}
      >
        {/* Logo/Brand */}
        {logo && <div className="flex-shrink-0">{logo}</div>}

        {/* Desktop Navigation Items */}
        <div className="hidden md:flex items-center space-x-1">{children}</div>

        {/* Actions and Mobile Menu Toggle */}
        <div className="flex items-center space-x-2">
          {actions}

          {showMobileToggle && (
            <button
              onClick={onMobileMenuToggle}
              className={cn(
                navigationItemVariants({ size: "mobile-touch" }),
                "md:hidden",
              )}
              aria-label={
                mobileMenuOpen
                  ? "Close navigation menu"
                  : "Open navigation menu"
              }
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-navigation-menu"
            >
              <svg
                className={cn(
                  "h-5 w-5 transition-transform duration-200",
                  mobileMenuOpen && "rotate-90",
                )}
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  d={
                    mobileMenuOpen
                      ? "M6 18L18 6M6 6l12 12"
                      : "M4 6h16M4 12h16M4 18h16"
                  }
                />
              </svg>
            </button>
          )}
        </div>

        {/* Mobile Navigation Menu */}
        {showMobileToggle && (
          <div
            id="mobile-navigation-menu"
            className={cn(
              "absolute top-full left-0 right-0 bg-background border-b border-border shadow-lg md:hidden transition-all duration-200 origin-top",
              mobileMenuOpen
                ? "scale-y-100 opacity-100"
                : "scale-y-0 opacity-0 pointer-events-none",
            )}
            role="menu"
            aria-label="Mobile navigation menu"
          >
            <div className="flex flex-col p-4 space-y-2">{children}</div>
          </div>
        )}
      </nav>
    );
  },
);
Navigation.displayName = "Navigation";

const NavigationItem = React.forwardRef<HTMLAnchorElement, NavigationItemProps>(
  (
    {
      className,
      variant,
      size,
      active = false,
      icon,
      asButton = false,
      onClick,
      children,
      ...props
    },
    ref,
  ) => {
    const itemVariant = active ? "active" : variant;
    const commonClassName = cn(
      navigationItemVariants({ variant: itemVariant, size }),
      className,
    );

    if (asButton) {
      return (
        <button
          ref={ref as React.Ref<HTMLButtonElement>}
          className={commonClassName}
          onClick={onClick}
          role="menuitem"
          {...(props as React.ButtonHTMLAttributes<HTMLButtonElement>)}
        >
          {icon && (
            <span className="mr-2" aria-hidden="true">
              {icon}
            </span>
          )}
          {children}
        </button>
      );
    }

    return (
      <a
        ref={ref}
        className={commonClassName}
        role="menuitem"
        aria-current={active ? "page" : undefined}
        {...props}
      >
        {icon && (
          <span className="mr-2" aria-hidden="true">
            {icon}
          </span>
        )}
        {children}
      </a>
    );
  },
);
NavigationItem.displayName = "NavigationItem";

export {
  Navigation,
  NavigationItem,
  navigationVariants,
  navigationItemVariants,
};
