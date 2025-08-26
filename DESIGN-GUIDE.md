# Eloquent AI Chat UI Design System

*A minimal, focused design language for conversational AI interfaces*

---

## 1. Core Principles

### **Conversational Flow First**
Every design decision prioritizes the natural flow of conversation. The interface disappears, letting the dialogue take center stage.

### **Thoughtful Minimalism**
Less chrome, more content. Every UI element earns its place through clear utility. No decoration without purpose.

### **Responsive Intelligence**
The interface should feel alive but not distracting. Subtle animations communicate system state without interrupting thought.

### **Unified Experience**
Both user and AI messages share the same visual space, creating a cohesive conversational thread rather than a divided interface.

---

## 2. Color System

### Base Palette
```css
/* Core colors from your existing theme */
--chat-background: var(--background);        /* #faf9f5 */
--chat-surface: var(--card);                /* #faf9f5 */
--chat-text-primary: var(--foreground);     /* #3d3929 */
--chat-text-secondary: var(--muted-foreground); /* #83827d */
--chat-border: var(--border);               /* #dad9d4 */

/* Message-specific */
--message-user-bg: var(--secondary);        /* #e9e6dc */
--message-ai-bg: var(--background);         /* #faf9f5 */
--message-hover: var(--accent);             /* #e9e6dc */

/* Interactive states */
--input-border: var(--input);               /* #b4b2a7 */
--input-focus: var(--primary);              /* #c96442 */
--button-primary: var(--primary);           /* #c96442 */

/* System states */
--error-bg: rgba(193, 100, 66, 0.1);
--error-border: var(--primary);
--code-bg: var(--muted);                    /* #ede9de */
```

### Dark Mode
```css
/* Automatically inherits from .dark class */
--chat-background: var(--background);        /* #262624 */
--message-user-bg: rgba(194, 122, 255, 0.1); /* Subtle purple tint */
--message-ai-bg: var(--background);
```

---

## 3. Typography

### Scale & Hierarchy
```css
/* Base */
--text-xs: 0.75rem;     /* 12px - timestamps, metadata */
--text-sm: 0.875rem;    /* 14px - secondary text */
--text-base: 0.9375rem; /* 15px - message body */
--text-lg: 1.125rem;    /* 18px - headings */

/* Line heights */
--leading-relaxed: 1.625; /* Message content */
--leading-normal: 1.5;    /* UI text */

/* Font weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
```

### Font Stack
```css
--font-chat: var(--font-sans);
--font-code: var(--font-mono);
```

### Message Typography
- **User messages**: `--text-base`, `--font-normal`, `--leading-relaxed`
- **AI responses**: `--text-base`, `--font-normal`, `--leading-relaxed`
- **Timestamps**: `--text-xs`, `--font-normal`, `--text-secondary`
- **System messages**: `--text-sm`, `--font-medium`, `--text-secondary`

---

## 4. Layout & Spacing

### Container Structure
```css
/* Main chat container */
.chat-container {
  max-width: 48rem;        /* 768px */
  margin: 0 auto;
  padding: 0 1rem;
}

/* Message spacing */
--message-gap: 1.5rem;     /* Between message groups */
--message-padding: 0.75rem 1rem;
--message-max-width: 85%;  /* Prevents full-width messages */

/* Input area */
--input-max-width: 48rem;
--input-padding: 1rem;
--input-margin: 1rem;
```

### Responsive Breakpoints
```css
/* Mobile: < 640px */
--chat-padding-mobile: 0.75rem;
--message-padding-mobile: 0.625rem 0.875rem;

/* Tablet: 640px - 1024px */
--chat-padding-tablet: 1rem;

/* Desktop: > 1024px */
--chat-padding-desktop: 1.5rem;
```

---

## 5. Component Patterns

### Message Components

#### Standard Message
```css
.message {
  /* Unified left-alignment for both user and AI */
  margin-left: 0;
  margin-bottom: var(--message-gap);
  max-width: var(--message-max-width);
}

.message-content {
  padding: var(--message-padding);
  border-radius: var(--radius-lg);
  background: transparent; /* No background by default */
}

.message--user .message-content {
  background: var(--message-user-bg);
  margin-left: 2rem; /* Slight indent for user messages */
}

.message--ai .message-content {
  background: var(--message-ai-bg);
  border: 1px solid var(--chat-border);
}
```

#### Message States
- **Streaming**: Cursor animation at end of text
- **Thinking**: Three-dot loader with subtle fade animation
- **Error**: Red-tinted background with error icon
- **Edited**: Small "edited" indicator below message

### Thinking Indicator
```css
.thinking-indicator {
  display: flex;
  gap: 0.25rem;
  padding: 0.75rem 1rem;
}

.thinking-dot {
  width: 0.5rem;
  height: 0.5rem;
  background: var(--text-secondary);
  border-radius: 50%;
  animation: thinking-pulse 1.4s ease-in-out infinite;
}

@keyframes thinking-pulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

/* Stagger the animation */
.thinking-dot:nth-child(1) { animation-delay: 0s; }
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }
```

### Input Area
```css
.input-container {
  background: var(--chat-surface);
  border: 1px solid var(--input-border);
  border-radius: var(--radius-lg);
  transition: border-color 0.2s ease;
}

.input-container:focus-within {
  border-color: var(--input-focus);
  box-shadow: 0 0 0 3px rgba(201, 100, 66, 0.1);
}

.input-textarea {
  min-height: 3rem;
  max-height: 12rem;
  resize: none;
  background: transparent;
}
```

---

## 6. Micro-interactions

### Animation Timings
```css
--duration-instant: 50ms;
--duration-fast: 150ms;
--duration-normal: 250ms;
--duration-slow: 350ms;

--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out: cubic-bezier(0.45, 0, 0.55, 1);
```

### Message Appearance
```css
@keyframes message-enter {
  from {
    opacity: 0;
    transform: translateY(0.5rem);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-new {
  animation: message-enter var(--duration-normal) var(--ease-out);
}
```

### Smooth Scrolling
```javascript
// Smooth scroll to bottom on new messages
scrollBehavior: 'smooth'
scrollMargin: '1rem'

// Auto-scroll only if user is near bottom
const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
if (isNearBottom) {
  scrollToBottom({ behavior: 'smooth' });
}
```

### Typing Animation
```css
.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 1.2em;
  background: var(--text-primary);
  animation: cursor-blink 1s step-end infinite;
}

@keyframes cursor-blink {
  50% { opacity: 0; }
}
```

---

## 7. Specialized Content

### Code Blocks
```css
.code-block {
  background: var(--code-bg);
  border: 1px solid var(--chat-border);
  border-radius: var(--radius-md);
  padding: 1rem;
  overflow-x: auto;
  font-family: var(--font-code);
  font-size: 0.875rem;
}

.code-block-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
```

### Citations & Sources
```css
.citation {
  display: inline;
  color: var(--primary);
  text-decoration: underline;
  text-decoration-color: rgba(201, 100, 66, 0.3);
  cursor: pointer;
}

.citation:hover {
  text-decoration-color: var(--primary);
}

.source-list {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--chat-border);
  font-size: var(--text-sm);
}
```

---

## 8. Sidebar & Navigation

### Collapsible Sidebar
```css
.sidebar {
  width: 16rem;
  background: var(--sidebar);
  border-right: 1px solid var(--sidebar-border);
  transition: transform var(--duration-normal) var(--ease-out);
}

.sidebar--collapsed {
  transform: translateX(-100%);
}

/* Smooth collapse animation */
@media (min-width: 1024px) {
  .sidebar {
    transition: width var(--duration-normal) var(--ease-out);
  }
  
  .sidebar--collapsed {
    width: 0;
    transform: none;
  }
}
```

### Header
```css
.header {
  height: 3.5rem;
  background: var(--chat-surface);
  border-bottom: 1px solid var(--chat-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
}

.header-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}
```

---

## 9. State Management

### Loading States
```css
/* Skeleton loader for messages */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--muted) 25%,
    var(--accent) 50%,
    var(--muted) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### Empty State
```css
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--text-secondary);
}

.empty-state-title {
  font-size: var(--text-lg);
  font-weight: var(--font-medium);
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}
```

---

## 10. Accessibility Patterns

### Focus Management
```css
/* Focus visible styles */
:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

/* Skip to content link */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  z-index: 100;
}

.skip-link:focus {
  top: 0;
}
```

### ARIA Labels
```html
<!-- Message structure -->
<div role="article" aria-label="Chat message">
  <div aria-label="User message" class="message--user">
  <div aria-label="AI response" class="message--ai">
</div>

<!-- Loading states -->
<div role="status" aria-live="polite" aria-label="AI is thinking">
```

---

## 11. Implementation Examples

### Basic Chat Layout
```html
<div class="chat-container">
  <div class="message message--user">
    <div class="message-content">
      <p>How do I implement authentication in my Next.js app?</p>
    </div>
    <div class="message-timestamp">2:14 PM</div>
  </div>
  
  <div class="message message--ai">
    <div class="message-content">
      <p>There are several approaches to authentication in Next.js...</p>
    </div>
    <div class="message-timestamp">2:14 PM</div>
  </div>
</div>
```

### Thinking Indicator Component
```html
<div class="message message--ai">
  <div class="thinking-indicator">
    <div class="thinking-dot"></div>
    <div class="thinking-dot"></div>
    <div class="thinking-dot"></div>
  </div>
</div>
```

### Input Component
```html
<div class="input-container">
  <textarea 
    class="input-textarea" 
    placeholder="Message Eloquent AI..."
    rows="1"
  ></textarea>
  <button class="send-button" type="submit">
    <svg><!-- Send icon --></svg>
  </button>
</div>
```

### Code Block with Syntax Highlighting
```html
<div class="code-block">
  <div class="code-block-header">
    <span class="language">javascript</span>
    <button class="copy-button">Copy</button>
  </div>
  <pre><code class="language-javascript">
const handleSubmit = async (message) => {
  setLoading(true);
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message })
    });
    const data = await response.json();
    setMessages(prev => [...prev, data]);
  } catch (error) {
    console.error(error);
  } finally {
    setLoading(false);
  }
};
  </code></pre>
</div>
```

---

## Implementation Notes

### Component Integration
- Use **shadcn/ui** base components with custom styling overrides
- Leverage **Radix UI** primitives for complex interactions (dropdowns, tooltips)
- Apply custom CSS variables through Tailwind's `theme()` function

### Performance Considerations
- Virtualize long chat histories (100+ messages)
- Lazy load images and heavy content
- Debounce input resize calculations
- Use CSS transforms for animations (GPU-accelerated)

### Mobile Optimizations
- Touch-friendly tap targets (min 44x44px)
- Momentum scrolling for chat history
- Collapsed sidebar by default on mobile
- Larger input text on mobile (16px minimum to prevent zoom)

---

## Quick Start Checklist

### Essential Components
- [ ] Message container with user/AI variants
- [ ] Input area with auto-resize textarea
- [ ] Thinking indicator animation
- [ ] Code block with syntax highlighting
- [ ] Loading states and error handling

### Styling Setup
- [ ] Import CSS custom properties
- [ ] Configure dark mode toggle
- [ ] Set up responsive breakpoints
- [ ] Add animation keyframes
- [ ] Test accessibility patterns

### Interactive Features
- [ ] Auto-scroll on new messages
- [ ] Message streaming animation
- [ ] Copy code functionality
- [ ] Keyboard shortcuts (Enter to send, Shift+Enter for new line)
- [ ] Focus management for screen readers

---
