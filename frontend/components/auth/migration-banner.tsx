"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { X, Users } from "lucide-react";
import Link from "next/link";

interface MigrationBannerProps {
  className?: string;
}

export function MigrationBanner({ className }: MigrationBannerProps) {
  const { isSignedIn, isLoaded } = useAuth();
  const [dismissed, setDismissed] = useState(false);

  // Don't show if user is already signed in, not loaded, or banner was dismissed
  if (!isLoaded || isSignedIn || dismissed) {
    return null;
  }

  return (
    <Card
      className={`border-primary/20 bg-primary/5 ${className}`}
      role="banner"
      aria-labelledby="migration-banner-title"
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 text-primary" aria-hidden="true" />
            <div>
              <CardTitle id="migration-banner-title" className="text-base">
                Save Your Chat History
              </CardTitle>
              <CardDescription className="text-sm">
                Sign up for free to save your conversations and access them from
                any device
              </CardDescription>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-8 h-8 p-0 hover:bg-destructive/10 hover:text-destructive"
            onClick={() => setDismissed(true)}
            aria-label="Dismiss migration banner"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div
          className="flex items-center gap-2"
          role="group"
          aria-label="Account actions"
        >
          <Button size="sm" asChild>
            <Link
              href="/sign-up?redirect_url=/"
              aria-label="Create free account to save chat history"
            >
              Create Account
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link
              href="/sign-in?redirect_url=/"
              aria-label="Sign in to existing account"
            >
              Sign In
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
