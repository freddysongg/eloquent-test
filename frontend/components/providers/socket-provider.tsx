"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
// Using native WebSocket instead of Socket.IO to match backend
// import { io, Socket } from "socket.io-client";
import { useAuth } from "@/components/providers/auth-provider";
import { buildWebSocketUrl } from "@/lib/api";

interface SocketContextType {
  socket: WebSocket | null;
  isConnected: boolean;
  connect: (chatId?: string) => void;
  disconnect: () => void;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

interface SocketProviderProps {
  children: React.ReactNode;
}

export function SocketProvider({ children }: SocketProviderProps) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const { user, isLoaded } = useAuth();
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const currentChatIdRef = useRef<string>("");

  // Store connect function in a ref to avoid circular dependency
  const connectRef = useRef<(chatId?: string) => void>();

  const handleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      // Max reconnection attempts reached
      return;
    }

    const delay = Math.min(
      1000 * Math.pow(2, reconnectAttemptsRef.current),
      30000,
    );

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptsRef.current += 1;
      // Reconnection attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}
      connectRef.current?.(currentChatIdRef.current);
    }, delay);
  }, []);

  const connect = useCallback(
    (chatId?: string) => {
      if (socket && socket.readyState === WebSocket.OPEN) return;

      // Update current chat ID for reconnection
      if (chatId) {
        currentChatIdRef.current = chatId;
      }

      const chatIdParam = currentChatIdRef.current || "default";
      const userId = user?.id || "anonymous";
      const socketUrl = buildWebSocketUrl(chatIdParam, userId);

      console.log("Connecting WebSocket to:", socketUrl);

      try {
        const newSocket = new WebSocket(socketUrl);

        newSocket.onopen = () => {
          console.log("WebSocket connected");
          setIsConnected(true);
          reconnectAttemptsRef.current = 0;
        };

        newSocket.onclose = (event) => {
          console.log("WebSocket disconnected:", event.code, event.reason);
          setIsConnected(false);

          // Reconnect unless it was a clean close
          if (event.code !== 1000 && event.code !== 1001) {
            handleReconnect();
          }
        };

        newSocket.onerror = (error) => {
          console.error("WebSocket error:", error);
          setIsConnected(false);
          handleReconnect();
        };

        newSocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const sanitizedData = sanitizeForLogging(data);
            // Log as a JSON string to clearly indicate user input and avoid injection
            console.log("Received WebSocket message (sanitized): " + JSON.stringify(sanitizedData));

            // Handle different message types
            switch (data.type) {
              case "message_received":
                // Handle incoming chat messages
                break;
              case "typing_start":
                // Handle typing indicators
                break;
              case "typing_stop":
                // Handle typing indicators
                break;
              case "error":
                console.error("WebSocket message error:", data.error);
                break;
              default:
                console.log("Unknown WebSocket message type:", data.type);
            }
          } catch (error) {
            console.error("Failed to parse WebSocket message:", error);
          }
        };

        setSocket(newSocket);
      } catch (error) {
        console.error("Failed to create WebSocket:", error);
        handleReconnect();
      }
    },
    [socket, user, handleReconnect],
  );

  // Update the ref whenever connect changes
  connectRef.current = connect;

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (socket) {
      socket.close(1000, "Client disconnecting");
      setSocket(null);
      setIsConnected(false);
      reconnectAttemptsRef.current = 0;
      currentChatIdRef.current = "";
    }
  }, [socket]);

  // Auto-connect when auth is loaded
  useEffect(() => {
    if (isLoaded) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [isLoaded, user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  const value: SocketContextType = {
    socket,
    isConnected,
    connect,
    disconnect,
  };

  return (
    <SocketContext.Provider value={value}>{children}</SocketContext.Provider>
  );
}

  const context = useContext(SocketContext);
  if (context === undefined) {
    throw new Error("useSocket must be used within a SocketProvider");
  }
  return context;
}
