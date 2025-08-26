"use client";

import { SignIn } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function SignInPage() {
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect_url");

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/50 p-4">
      <div className="w-full max-w-md">
        <Card className="border-0 shadow-lg">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-bold">
              Welcome to Eloquent AI
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Sign in to access your chat history and personalized experience
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <SignIn
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
              signUpUrl="/sign-up"
            />
          </CardContent>
        </Card>

        {/* Features */}
        <div className="mt-8 text-center">
          <p className="text-sm text-muted-foreground mb-4">
            Why sign up for Eloquent AI?
          </p>
          <div className="grid gap-3 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full" />
              <span className="text-muted-foreground">
                Save and access your chat history
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full" />
              <span className="text-muted-foreground">
                Personalized AI responses
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full" />
              <span className="text-muted-foreground">
                Sync across all your devices
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
