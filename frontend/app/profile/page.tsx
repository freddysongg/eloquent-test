"use client";

import { UserProfile } from "@clerk/nextjs";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ProfilePage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/20">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/">
                <span className="flex items-center gap-2">
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back to Chat</span>
                </span>
              </Link>
            </Button>
            <div>
              <h1 className="text-2xl font-bold">Profile Settings</h1>
              <p className="text-muted-foreground">
                Manage your account settings and preferences
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle>Account Management</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <UserProfile
                appearance={{
                  elements: {
                    rootBox: "w-full",
                    card: "border-0 shadow-none bg-transparent",
                    navbar: "bg-muted/20",
                    navbarButton: "text-foreground hover:bg-muted/50",
                    navbarButtonIcon: "text-muted-foreground",
                    headerTitle: "text-foreground",
                    headerSubtitle: "text-muted-foreground",
                    formFieldInput:
                      "bg-background border-input focus:border-ring text-foreground",
                    formFieldLabel: "text-foreground",
                    formButtonPrimary:
                      "bg-primary text-primary-foreground hover:bg-primary/90",
                    formButtonSecondary:
                      "bg-secondary text-secondary-foreground hover:bg-secondary/80",
                    identityPreviewText: "text-foreground",
                    identityPreviewEditButton:
                      "text-primary hover:text-primary/80",
                    accordionTriggerButton: "text-foreground hover:bg-muted/50",
                    accordionContent: "text-muted-foreground",
                    profileSectionPrimaryButton:
                      "bg-primary text-primary-foreground hover:bg-primary/90",
                    breadcrumbsLink: "text-primary hover:text-primary/80",
                    breadcrumbsLinkCurrent: "text-foreground",
                  },
                }}
                path="/profile"
                routing="path"
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
