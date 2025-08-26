"use client";

import { useState, useEffect, useCallback } from "react";

interface SidebarState {
  isCollapsed: boolean;
  isMobileOpen: boolean;
  width: number;
}

interface UseSidebarReturn {
  // State
  isCollapsed: boolean;
  isMobileOpen: boolean;
  width: number;

  // Desktop actions
  toggleCollapsed: () => void;
  setCollapsed: (collapsed: boolean) => void;

  // Mobile actions
  openMobile: () => void;
  closeMobile: () => void;
  toggleMobile: () => void;

  // Responsive helpers
  isMobile: boolean;
  isDesktop: boolean;

  // Accessibility helpers
  getAriaLabel: () => string;
  getAriaExpanded: () => boolean;
}

const STORAGE_KEY = "sidebar-state";
const COLLAPSED_WIDTH = 64; // Width when collapsed (icon-only)
const EXPANDED_WIDTH = 256; // Width when expanded (md:w-64 equivalent)

/**
 * Custom hook for managing sidebar state with persistent storage
 * Handles both desktop collapse/expand and mobile overlay states
 */
export function useSidebar(): UseSidebarReturn {
  const [state, setState] = useState<SidebarState>({
    isCollapsed: false,
    isMobileOpen: false,
    width: EXPANDED_WIDTH,
  });

  const [isMobile, setIsMobile] = useState(false);

  // Load persisted state on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsedState = JSON.parse(stored) as Partial<SidebarState>;
        setState((prev) => ({
          ...prev,
          isCollapsed: parsedState.isCollapsed ?? false,
          width: parsedState.isCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH,
        }));
      } catch (error) {
        console.warn("Failed to parse sidebar state from localStorage:", error);
      }
    }
  }, []);

  // Handle responsive breakpoint detection
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.matchMedia("(max-width: 768px)").matches;
      setIsMobile(mobile);

      // Auto-close mobile sidebar when switching to desktop
      if (!mobile && state.isMobileOpen) {
        setState((prev) => ({ ...prev, isMobileOpen: false }));
      }
    };

    checkMobile();

    const mediaQuery = window.matchMedia("(max-width: 768px)");
    mediaQuery.addEventListener("change", checkMobile);

    return () => mediaQuery.removeEventListener("change", checkMobile);
  }, [state.isMobileOpen]);

  // Persist state changes
  const persistState = useCallback((newState: Partial<SidebarState>) => {
    const stateToStore = {
      isCollapsed: newState.isCollapsed,
      // Don't persist mobile state or width (calculated)
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToStore));
  }, []);

  // Desktop collapse/expand actions
  const toggleCollapsed = useCallback(() => {
    setState((prev) => {
      const newCollapsed = !prev.isCollapsed;
      const newWidth = newCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH;
      const newState = { ...prev, isCollapsed: newCollapsed, width: newWidth };

      persistState(newState);
      return newState;
    });
  }, [persistState]);

  const setCollapsed = useCallback(
    (collapsed: boolean) => {
      setState((prev) => {
        if (prev.isCollapsed === collapsed) return prev;

        const newWidth = collapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH;
        const newState = { ...prev, isCollapsed: collapsed, width: newWidth };

        persistState(newState);
        return newState;
      });
    },
    [persistState],
  );

  // Mobile overlay actions
  const openMobile = useCallback(() => {
    setState((prev) => ({ ...prev, isMobileOpen: true }));
  }, []);

  const closeMobile = useCallback(() => {
    setState((prev) => ({ ...prev, isMobileOpen: false }));
  }, []);

  const toggleMobile = useCallback(() => {
    setState((prev) => ({ ...prev, isMobileOpen: !prev.isMobileOpen }));
  }, []);

  // Accessibility helpers
  const getAriaLabel = useCallback(() => {
    if (isMobile) {
      return state.isMobileOpen
        ? "Close navigation menu"
        : "Open navigation menu";
    }
    return state.isCollapsed ? "Expand sidebar" : "Collapse sidebar";
  }, [isMobile, state.isCollapsed, state.isMobileOpen]);

  const getAriaExpanded = useCallback(() => {
    return isMobile ? state.isMobileOpen : !state.isCollapsed;
  }, [isMobile, state.isCollapsed, state.isMobileOpen]);

  return {
    // State
    isCollapsed: state.isCollapsed,
    isMobileOpen: state.isMobileOpen,
    width: state.width,

    // Desktop actions
    toggleCollapsed,
    setCollapsed,

    // Mobile actions
    openMobile,
    closeMobile,
    toggleMobile,

    // Responsive helpers
    isMobile,
    isDesktop: !isMobile,

    // Accessibility helpers
    getAriaLabel,
    getAriaExpanded,
  };
}
