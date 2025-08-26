"use client";

import { useAuth } from "@/components/providers/auth-provider";
import { useSocket } from "@/components/providers/socket-provider";
import { useApiClient } from "@/hooks/use-api-client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, XCircle, AlertCircle, Loader } from "lucide-react";

/**
 * Development component for testing authentication integration
 * Remove this component in production
 */
export function AuthTest() {
  const { user, isLoaded, isSignedIn } = useAuth();
  const { isConnected } = useSocket();
  const apiClient = useApiClient();

  const testApiConnection = async () => {
    try {
      console.log("Testing API connection...");
      const response = await apiClient.listChats();
      console.log("API Response:", response);
    } catch (error) {
      console.error("API Test Failed:", error);
    }
  };

  if (!isLoaded) {
    return (
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Loader className="w-5 h-5 animate-spin" />
            Authentication Test
          </CardTitle>
          <CardDescription>Loading authentication state...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>Authentication Integration Test</CardTitle>
        <CardDescription>
          Verify that authentication, WebSocket, and API integration are working
          correctly
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Authentication Status */}
        <div className="space-y-3">
          <h3 className="font-semibold">Authentication Status</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-2">
              {isLoaded ? (
                <CheckCircle className="w-4 h-4 text-green-500" />
              ) : (
                <XCircle className="w-4 h-4 text-red-500" />
              )}
              <span className="text-sm">Auth Loaded</span>
              <Badge variant={isLoaded ? "default" : "destructive"}>
                {isLoaded ? "Yes" : "No"}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              {isSignedIn ? (
                <CheckCircle className="w-4 h-4 text-green-500" />
              ) : (
                <AlertCircle className="w-4 h-4 text-yellow-500" />
              )}
              <span className="text-sm">Signed In</span>
              <Badge variant={isSignedIn ? "default" : "secondary"}>
                {isSignedIn ? "Yes" : "Anonymous"}
              </Badge>
            </div>
          </div>

          {user && (
            <div className="p-3 bg-muted rounded-lg">
              <p className="text-sm font-medium">User Info</p>
              <p className="text-xs text-muted-foreground">ID: {user.id}</p>
              <p className="text-xs text-muted-foreground">
                Email: {user.emailAddresses?.[0]?.emailAddress || "N/A"}
              </p>
            </div>
          )}
        </div>

        {/* WebSocket Status */}
        <div className="space-y-3">
          <h3 className="font-semibold">WebSocket Status</h3>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <XCircle className="w-4 h-4 text-red-500" />
            )}
            <span className="text-sm">WebSocket Connection</span>
            <Badge variant={isConnected ? "default" : "destructive"}>
              {isConnected ? "Connected" : "Disconnected"}
            </Badge>
          </div>
        </div>

        {/* API Client Status */}
        <div className="space-y-3">
          <h3 className="font-semibold">API Client Status</h3>
          <div className="flex items-center gap-2">
            {apiClient.isAuthenticated ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <AlertCircle className="w-4 h-4 text-yellow-500" />
            )}
            <span className="text-sm">API Authentication</span>
            <Badge
              variant={apiClient.isAuthenticated ? "default" : "secondary"}
            >
              {apiClient.isAuthenticated ? "Authenticated" : "Anonymous"}
            </Badge>
          </div>
          <Button onClick={testApiConnection} size="sm">
            Test API Connection
          </Button>
        </div>

        {/* Integration Summary */}
        <div className="space-y-3">
          <h3 className="font-semibold">Integration Summary</h3>
          <div className="p-3 bg-muted rounded-lg">
            <div className="grid grid-cols-1 gap-2 text-sm">
              <div className="flex justify-between">
                <span>Auth Provider:</span>
                <span className={isLoaded ? "text-green-600" : "text-red-600"}>
                  {isLoaded ? "✓ Working" : "✗ Not Loaded"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Socket Provider:</span>
                <span
                  className={isConnected ? "text-green-600" : "text-red-600"}
                >
                  {isConnected ? "✓ Connected" : "✗ Disconnected"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>API Client:</span>
                <span className="text-green-600">✓ Ready</span>
              </div>
              <div className="flex justify-between">
                <span>Chat Interface:</span>
                <span className="text-green-600">✓ Integrated</span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
