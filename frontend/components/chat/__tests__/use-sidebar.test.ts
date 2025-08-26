/**
 * @jest-environment jsdom
 */

import { renderHook, act } from "@testing-library/react";
import { useSidebar } from "../../../hooks/use-sidebar";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

describe("useSidebar", () => {
  beforeEach(() => {
    localStorageMock.clear();
    jest.clearAllMocks();
  });

  it("should initialize with default state", () => {
    const { result } = renderHook(() => useSidebar());

    expect(result.current.isCollapsed).toBe(false);
    expect(result.current.isMobileOpen).toBe(false);
    expect(result.current.width).toBe(256); // EXPANDED_WIDTH
    expect(result.current.isMobile).toBe(false);
    expect(result.current.isDesktop).toBe(true);
  });

  it("should toggle collapsed state", () => {
    const { result } = renderHook(() => useSidebar());

    act(() => {
      result.current.toggleCollapsed();
    });

    expect(result.current.isCollapsed).toBe(true);
    expect(result.current.width).toBe(64); // COLLAPSED_WIDTH

    act(() => {
      result.current.toggleCollapsed();
    });

    expect(result.current.isCollapsed).toBe(false);
    expect(result.current.width).toBe(256); // EXPANDED_WIDTH
  });

  it("should set collapsed state explicitly", () => {
    const { result } = renderHook(() => useSidebar());

    act(() => {
      result.current.setCollapsed(true);
    });

    expect(result.current.isCollapsed).toBe(true);
    expect(result.current.width).toBe(64);

    act(() => {
      result.current.setCollapsed(false);
    });

    expect(result.current.isCollapsed).toBe(false);
    expect(result.current.width).toBe(256);
  });

  it("should handle mobile sidebar state", () => {
    const { result } = renderHook(() => useSidebar());

    act(() => {
      result.current.openMobile();
    });

    expect(result.current.isMobileOpen).toBe(true);

    act(() => {
      result.current.closeMobile();
    });

    expect(result.current.isMobileOpen).toBe(false);

    act(() => {
      result.current.toggleMobile();
    });

    expect(result.current.isMobileOpen).toBe(true);
  });

  it("should persist collapsed state to localStorage", () => {
    const { result } = renderHook(() => useSidebar());

    act(() => {
      result.current.setCollapsed(true);
    });

    const stored = localStorage.getItem("sidebar-state");
    expect(stored).toBeTruthy();

    const parsedState = JSON.parse(stored!);
    expect(parsedState.isCollapsed).toBe(true);
  });

  it("should load persisted state from localStorage", () => {
    // Pre-populate localStorage
    localStorage.setItem(
      "sidebar-state",
      JSON.stringify({ isCollapsed: true }),
    );

    const { result } = renderHook(() => useSidebar());

    expect(result.current.isCollapsed).toBe(true);
    expect(result.current.width).toBe(64);
  });

  it("should handle invalid localStorage data gracefully", () => {
    localStorage.setItem("sidebar-state", "invalid-json");

    const { result } = renderHook(() => useSidebar());

    // Should use default state when localStorage data is invalid
    expect(result.current.isCollapsed).toBe(false);
    expect(result.current.width).toBe(256);
  });

  it("should not persist mobile state", () => {
    const { result } = renderHook(() => useSidebar());

    act(() => {
      result.current.openMobile();
    });

    const stored = localStorage.getItem("sidebar-state");
    const parsedState = JSON.parse(stored!);

    // Mobile state should not be persisted
    expect(parsedState.isMobileOpen).toBeUndefined();
  });
});
