import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Enhanced semantic color tokens
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        // Surface tokens
        surface: {
          DEFAULT: "hsl(var(--background))",
          elevated: "hsl(var(--surface-elevated))",
          hover: "hsl(var(--surface-hover))",
          pressed: "hsl(var(--surface-pressed))",
          disabled: "hsl(var(--surface-disabled))",
        },
        // Interactive tokens
        interactive: {
          DEFAULT: "hsl(var(--interactive-default))",
          hover: "hsl(var(--interactive-hover))",
          pressed: "hsl(var(--interactive-pressed))",
          disabled: "hsl(var(--interactive-disabled))",
        },
        // Semantic text tokens
        text: {
          primary: "hsl(var(--text-primary))",
          secondary: "hsl(var(--text-secondary))",
          tertiary: "hsl(var(--text-tertiary))",
          disabled: "hsl(var(--text-disabled))",
          inverse: "hsl(var(--text-inverse))",
        },
        // Semantic border tokens
        "border-semantic": {
          primary: "hsl(var(--border-primary))",
          secondary: "hsl(var(--border-secondary))",
          hover: "hsl(var(--border-hover))",
          focus: "hsl(var(--border-focus))",
          disabled: "hsl(var(--border-disabled))",
        },
      },
      backgroundImage: {
        "gradient-primary": "var(--gradient-primary)",
        "gradient-primary-hover": "var(--gradient-primary-hover)",
        "gradient-primary-subtle": "var(--gradient-primary-subtle)",
        "gradient-secondary": "var(--gradient-secondary)",
        "gradient-secondary-hover": "var(--gradient-secondary-hover)",
        "gradient-accent": "var(--gradient-accent)",
        "gradient-accent-warm": "var(--gradient-accent-warm)",
        "gradient-background": "var(--gradient-background)",
        "gradient-background-subtle": "var(--gradient-background-subtle)",
        "gradient-card": "var(--gradient-card)",
        "gradient-card-hover": "var(--gradient-card-hover)",
        "gradient-muted": "var(--gradient-muted)",
        "gradient-muted-subtle": "var(--gradient-muted-subtle)",
        "gradient-destructive": "var(--gradient-destructive)",
        "gradient-destructive-hover": "var(--gradient-destructive-hover)",
        "gradient-message-user": "var(--gradient-message-user)",
        "gradient-message-ai": "var(--gradient-message-ai)",
        "gradient-input-focus": "var(--gradient-input-focus)",
        "gradient-vertical": "var(--gradient-vertical)",
        "gradient-horizontal": "var(--gradient-horizontal)",
        "gradient-radial": "var(--gradient-radial)",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "slide-in-from-top": {
          from: { transform: "translateY(-100%)" },
          to: { transform: "translateY(0)" },
        },
        "slide-in-from-bottom": {
          from: { transform: "translateY(100%)" },
          to: { transform: "translateY(0)" },
        },
        "slide-in-from-left": {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(0)" },
        },
        "slide-in-from-right": {
          from: { transform: "translateX(100%)" },
          to: { transform: "translateX(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-out": {
          from: { opacity: "1" },
          to: { opacity: "0" },
        },
        "pulse-subtle": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.8" },
        },
        typing: {
          "0%": { width: "0ch" },
          "100%": { width: "100ch" },
        },
        blink: {
          "0%, 50%": { borderColor: "transparent" },
          "51%, 100%": { borderColor: "currentColor" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "slide-in-from-top": "slide-in-from-top 0.2s ease-out",
        "slide-in-from-bottom": "slide-in-from-bottom 0.2s ease-out",
        "slide-in-from-left": "slide-in-from-left 0.2s ease-out",
        "slide-in-from-right": "slide-in-from-right 0.2s ease-out",
        "fade-in": "fade-in 0.2s ease-out",
        "fade-out": "fade-out 0.2s ease-out",
        "pulse-subtle": "pulse-subtle 2s ease-in-out infinite",
        typing: "typing 2s steps(100, end)",
        blink: "blink 1s step-end infinite",
        // Semantic animation tokens
        "duration-fast": "var(--duration-fast)",
        "duration-normal": "var(--duration-normal)",
        "duration-slow": "var(--duration-slow)",
      },
      spacing: {
        "18": "4.5rem",
        "88": "22rem",
        // Semantic spacing tokens
        "space-xs": "var(--space-xs)",
        "space-sm": "var(--space-sm)",
        "space-md": "var(--space-md)",
        "space-lg": "var(--space-lg)",
        "space-xl": "var(--space-xl)",
        "space-2xl": "var(--space-2xl)",
      },
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1rem" }],
        sm: ["0.875rem", { lineHeight: "1.25rem" }],
        base: ["1rem", { lineHeight: "1.5rem" }],
        lg: ["1.125rem", { lineHeight: "1.75rem" }],
        xl: ["1.25rem", { lineHeight: "1.75rem" }],
        "2xl": ["1.5rem", { lineHeight: "2rem" }],
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],
        "4xl": ["2.25rem", { lineHeight: "2.5rem" }],
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: [
          "var(--font-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "monospace",
        ],
      },
      maxWidth: {
        "8xl": "88rem",
      },
      // Enhanced shadow tokens
      boxShadow: {
        "semantic-sm": "var(--shadow-sm)",
        "semantic-md": "var(--shadow-md)",
        "semantic-lg": "var(--shadow-lg)",
        "semantic-xl": "var(--shadow-xl)",
      },
      // Enhanced transition timing functions
      transitionTimingFunction: {
        "ease-linear": "var(--ease-linear)",
        "ease-in-custom": "var(--ease-in)",
        "ease-out-custom": "var(--ease-out)",
        "ease-in-out-custom": "var(--ease-in-out)",
        "ease-bounce": "var(--ease-bounce)",
      },
      // Enhanced transition durations
      transitionDuration: {
        instant: "var(--duration-instant)",
        fast: "var(--duration-fast)",
        normal: "var(--duration-normal)",
        slow: "var(--duration-slow)",
        slower: "var(--duration-slower)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
