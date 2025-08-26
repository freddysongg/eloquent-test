"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { X, Smartphone } from "lucide-react";
import Link from "next/link";

interface MobileAuthBannerProps {
  className?: string;
}

/**
 * Mobile-optimized authentication banner for anonymous users
 * Shows a compact, dismissible banner encouraging registration
 */
export function MobileAuthBanner({ className }: MobileAuthBannerProps) {
  const { isSignedIn, isLoaded } = useAuth();
  const [dismissed, setDismissed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);

    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Don't show if user is already signed in, not loaded, dismissed, or not mobile
  if (!isLoaded || isSignedIn || dismissed || !isMobile) {
    return null;
  }

  return (
    <div
      className={`sticky top-0 z-40 bg-primary/10 border-b border-primary/20 ${className}`}
    >
      <div className="flex items-center justify-between px-3 py-2 text-sm">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <Smartphone className="w-4 h-4 text-primary flex-shrink-0" />
          <span className="text-primary/90 truncate">
            Save your chats - Sign up free
          </span>
        </div>

        <div className="flex items-center gap-1 ml-2">
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs bg-primary/20 text-primary hover:bg-primary/30"
            asChild
          >
            <Link href="/sign-up?redirect_url=/">Sign Up</Link>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            className="w-7 h-7 p-0 hover:bg-primary/20"
            onClick={() => setDismissed(true)}
            aria-label="Dismiss banner"
          >
            <X className="w-3 h-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}
