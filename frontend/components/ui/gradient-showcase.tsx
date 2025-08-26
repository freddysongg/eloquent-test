/**
 * Gradient System Showcase Component
 *
 * This component demonstrates the various gradient utilities and patterns
 * available in the Eloquent AI design system. Use this as a reference
 * for implementing gradients in your components.
 */

import React from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface GradientShowcaseProps {
  className?: string;
}

export function GradientShowcase({ className }: GradientShowcaseProps) {
  return (
    <div className={cn("space-y-8 p-6", className)}>
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gradient-primary mb-2">
          Gradient System Showcase
        </h1>
        <p className="text-muted-foreground">
          Explore the gradient enhancements available in the design system
        </p>
      </div>

      {/* Button Variants */}
      <Card variant="gradient-subtle">
        <CardHeader>
          <CardTitle>Enhanced Button Variants</CardTitle>
          <CardDescription>
            Gradient button variants with interactive hover states
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <Button variant="gradient-primary">Primary Gradient</Button>
            <Button variant="gradient-secondary">Secondary Gradient</Button>
            <Button variant="gradient-accent">Accent Gradient</Button>
            <Button variant="gradient-destructive">Destructive Gradient</Button>
            <Button variant="gradient-subtle">Subtle Gradient</Button>
            <Button variant="gradient-glass">Glass Effect</Button>
          </div>
          <div className="text-sm text-muted-foreground">
            Hover over buttons to see gradient transitions
          </div>
        </CardContent>
      </Card>

      {/* Card Variants */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Enhanced Card Variants</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card variant="default">
            <CardContent className="pt-6">
              <div className="text-center">
                <h3 className="font-semibold">Default Card</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  Standard flat background
                </p>
              </div>
            </CardContent>
          </Card>

          <Card variant="gradient">
            <CardContent className="pt-6">
              <div className="text-center">
                <h3 className="font-semibold">Gradient Card</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  Enhanced with subtle gradient
                </p>
              </div>
            </CardContent>
          </Card>

          <Card variant="gradient-glass">
            <CardContent className="pt-6">
              <div className="text-center">
                <h3 className="font-semibold">Glass Card</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  Glass morphism effect
                </p>
              </div>
            </CardContent>
          </Card>

          <Card variant="gradient-message">
            <CardContent className="pt-6">
              <div className="text-center">
                <h3 className="font-semibold">Message Card</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  Chat-optimized gradient
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Background Gradients */}
      <Card>
        <CardHeader>
          <CardTitle>Background Gradient Utilities</CardTitle>
          <CardDescription>
            Various background gradient patterns for different use cases
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="bg-gradient-primary-subtle rounded-lg p-4 text-center">
              <div className="font-medium">Primary Subtle</div>
              <div className="text-sm text-muted-foreground mt-1">
                .bg-gradient-primary-subtle
              </div>
            </div>
            <div className="bg-gradient-muted-subtle rounded-lg p-4 text-center">
              <div className="font-medium">Muted Subtle</div>
              <div className="text-sm text-muted-foreground mt-1">
                .bg-gradient-muted-subtle
              </div>
            </div>
            <div className="bg-gradient-accent-warm rounded-lg p-4 text-center">
              <div className="font-medium">Accent Warm</div>
              <div className="text-sm text-muted-foreground mt-1">
                .bg-gradient-accent-warm
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Interactive Examples */}
      <Card variant="gradient-glass">
        <CardHeader>
          <CardTitle>Interactive Gradient States</CardTitle>
          <CardDescription>
            Hover effects and transitions using the gradient system
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="hover-gradient-primary rounded-lg p-6 text-center cursor-pointer transition-all duration-200 bg-card border">
              <div className="font-medium">Hover Primary</div>
              <div className="text-sm text-muted-foreground mt-1">
                Hover for gradient effect
              </div>
            </div>
            <div className="hover-gradient-card rounded-lg p-6 text-center cursor-pointer transition-all duration-200 bg-card border">
              <div className="font-medium">Hover Card</div>
              <div className="text-sm text-muted-foreground mt-1">
                Subtle hover enhancement
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Chat Message Examples */}
      <Card>
        <CardHeader>
          <CardTitle>Chat Interface Gradients</CardTitle>
          <CardDescription>
            Specialized gradients for conversational UI elements
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="bg-gradient-message-user text-primary-foreground rounded-lg p-4 ml-8 max-w-md">
              <div className="font-medium">User Message</div>
              <div className="text-sm opacity-90 mt-1">
                Enhanced with user message gradient
              </div>
            </div>
            <div className="bg-gradient-message-ai border rounded-lg p-4 mr-8 max-w-md">
              <div className="font-medium">AI Response</div>
              <div className="text-sm text-muted-foreground mt-1">
                Subtle AI message background gradient
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Text Gradients */}
      <Card>
        <CardHeader>
          <CardTitle className="text-gradient-primary">
            Text Gradient Examples
          </CardTitle>
          <CardDescription>
            Gradient text effects for headings and emphasis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-gradient-primary">
              Primary Text Gradient
            </h2>
            <h3 className="text-xl font-semibold text-gradient-secondary">
              Secondary Text Gradient
            </h3>
            <p className="text-gradient">Standard gradient text utility</p>
          </div>
        </CardContent>
      </Card>

      {/* Implementation Notes */}
      <Card variant="gradient-subtle">
        <CardHeader>
          <CardTitle>Implementation Notes</CardTitle>
          <CardDescription>
            Key points for using the gradient system effectively
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="text-sm space-y-2">
            <p>✓ All gradients automatically adapt to light/dark themes</p>
            <p>
              ✓ Backward compatibility maintained - existing components
              unchanged
            </p>
            <p>✓ Accessibility tested with WCAG 2.1 AA compliance</p>
            <p>✓ GPU-accelerated CSS for smooth 60fps animations</p>
            <p>✓ CSS custom properties enable easy customization</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default GradientShowcase;
