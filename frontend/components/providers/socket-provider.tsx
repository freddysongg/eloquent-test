'use client';

import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '@/components/providers/auth-provider';

interface SocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  connect: () => void;
  disconnect: () => void;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

interface SocketProviderProps {
  children: React.ReactNode;
}

export function SocketProvider({ children }: SocketProviderProps) {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const { user, isLoaded } = useAuth();
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  // Store connect function in a ref to avoid circular dependency
  const connectRef = useRef<() => void>();

  const handleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptsRef.current += 1;
      console.log(`Reconnection attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}`);
      connectRef.current?.();
    }, delay);
  }, []);

  const connect = useCallback(() => {
    if (socket?.connected) return;

    const socketUrl = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000';
    
    const newSocket = io(socketUrl, {
      ...(user && { auth: { userId: user.id } }),
      transports: ['websocket', 'polling'],
      timeout: 20000,
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: maxReconnectAttempts,
    });

    newSocket.on('connect', () => {
      console.log('Socket connected:', newSocket.id);
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
    });

    newSocket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason);
      setIsConnected(false);
      
      // Handle reconnection for certain disconnect reasons
      if (reason === 'io server disconnect') {
        // Server initiated disconnect, try to reconnect
        handleReconnect();
      }
    });

    newSocket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      setIsConnected(false);
      handleReconnect();
    });

    newSocket.on('error', (error) => {
      console.error('Socket error:', error);
    });

    // Chat-specific event listeners
    newSocket.on('message_received', (data) => {
      // Handle incoming messages
      console.log('Message received:', data);
    });

    newSocket.on('typing_start', (data) => {
      // Handle typing indicators
      console.log('Typing started:', data);
    });

    newSocket.on('typing_stop', (data) => {
      // Handle typing indicators
      console.log('Typing stopped:', data);
    });

    setSocket(newSocket);
  }, [socket, user, handleReconnect]);

  // Update the ref whenever connect changes
  connectRef.current = connect;

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (socket) {
      socket.disconnect();
      setSocket(null);
      setIsConnected(false);
      reconnectAttemptsRef.current = 0;
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
  }, [isLoaded, user?.id, connect, disconnect]); // Reconnect when user changes

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

  return <SocketContext.Provider value={value}>{children}</SocketContext.Provider>;
}

export function useSocket() {
  const context = useContext(SocketContext);
  if (context === undefined) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
}