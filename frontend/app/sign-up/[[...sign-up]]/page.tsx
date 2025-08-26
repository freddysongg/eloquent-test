"use client";

import { SignUp } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function SignUpPage() {
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect_url");

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/50 p-4">
      <div className="w-full max-w-md">
        <Card className="border-0 shadow-lg">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-bold">
              Join Eloquent AI
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Create your account to get started with personalized AI assistance
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <SignUp
              appearance={{
                elements: {
                  rootBox: "w-full",
                  card: "border-0 shadow-none bg-transparent",
                  headerTitle: "hidden",
                  headerSubtitle: "hidden",
                  socialButtonsBlockButton:
                    "bg-background hover:bg-muted border-input text-foreground",
                  socialButtonsBlockButtonText: "text-foreground",
                  dividerLine: "bg-border",
                  dividerText: "text-muted-foreground",
                  formFieldInput:
                    "bg-background border-input focus:border-ring text-foreground",
                  formFieldLabel: "text-foreground",
                  formButtonPrimary:
                    "bg-primary text-primary-foreground hover:bg-primary/90",
                  formFieldInputShowPasswordButton: "text-muted-foreground", // pragma: allowlist secret
                  identityPreviewEditButton:
                    "text-primary hover:text-primary/80",
                  formResendCodeLink: "text-primary hover:text-primary/80",
                  footer: "hidden",
                },
              }}
              fallbackRedirectUrl={redirectUrl || "/"}
              signInUrl="/sign-in"
            />
          </CardContent>
        </Card>

        {/* Benefits */}
        <div className="mt-8 text-center">
          <p className="text-sm text-muted-foreground mb-4">
            Get started with Eloquent AI today
          </p>
          <div className="grid gap-3 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full" />
              <span className="text-muted-foreground">
                Free account with unlimited basic queries
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full" />
              <span className="text-muted-foreground">
                Advanced fintech knowledge base
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full" />
              <span className="text-muted-foreground">
                Real-time AI-powered responses
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
