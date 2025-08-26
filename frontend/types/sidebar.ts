/**
 * TypeScript definitions for the collapsible sidebar system
 */

export interface SidebarState {
  /** Whether the sidebar is collapsed (desktop only) */
  isCollapsed: boolean;
  /** Whether the mobile sidebar overlay is open */
  isMobileOpen: boolean;
  /** Current width in pixels */
  width: number;
}

export interface SidebarActions {
  // Desktop actions
  toggleCollapsed: () => void;
  setCollapsed: (collapsed: boolean) => void;

  // Mobile actions
  openMobile: () => void;
  closeMobile: () => void;
  toggleMobile: () => void;
}

export interface SidebarHelpers {
  /** Whether currently on mobile breakpoint */
  isMobile: boolean;
  /** Whether currently on desktop breakpoint */
  isDesktop: boolean;
}

export interface UseSidebarReturn
  extends SidebarState,
    SidebarActions,
    SidebarHelpers {}

export interface CollapsibleSidebarProps {
  onChatSelect?: (chatId: string) => void;
  onNewChat?: () => void;
}

export interface ChatItemProps {
  chat: any; // TODO: Replace with proper chat type from chat.ts
  isActive: boolean;
  isCollapsed: boolean;
  onSelect: () => void;
  formatTitle: (chat: any) => string;
  formatTime: (chat: any) => string;
}

export interface MobileSidebarContentProps {
  chats: any[];
  groupedChats: Record<string, any[]>;
  currentChatId: string | null;
  isLoading: boolean;
  error: string | null;
  isSignedIn: boolean;
  onChatSelect: (chatId: string) => void;
  onNewChat: () => void;
  onClose: () => void;
  formatChatTitle: (chat: any) => string;
  formatChatTime: (chat: any) => string;
}

// Constants
export const SIDEBAR_WIDTHS = {
  COLLAPSED: 64,
  EXPANDED: 256,
  MOBILE: 320,
} as const;

export const BREAKPOINTS = {
  MOBILE: "(max-width: 768px)",
} as const;

export const STORAGE_KEYS = {
  SIDEBAR_STATE: "sidebar-state",
} as const;

// Animation durations (in ms)
export const ANIMATIONS = {
  SIDEBAR_TRANSITION: 300,
  MOBILE_SLIDE: 300,
} as const;
