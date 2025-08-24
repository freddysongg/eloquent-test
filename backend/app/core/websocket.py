"""
WebSocket connection manager for real-time chat functionality.

Manages WebSocket connections, message broadcasting, and connection lifecycle
with proper error handling and connection cleanup.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time chat functionality."""
    
    def __init__(self) -> None:
        """Initialize connection manager."""
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        # User ID to connection IDs mapping
        self.user_connections: Dict[str, Set[str]] = {}
        # Chat room to connection IDs mapping
        self.chat_connections: Dict[str, Set[str]] = {}
        
        logger.info("WebSocket connection manager initialized")
    
    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None
    ) -> str:
        """
        Accept WebSocket connection and register it.
        
        Args:
            websocket: WebSocket connection instance
            user_id: Optional authenticated user ID
            chat_id: Optional chat room ID
            
        Returns:
            Connection ID for tracking
        """
        await websocket.accept()
        
        connection_id = str(uuid4())
        self.active_connections[connection_id] = websocket
        
        # Track user connections
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        # Track chat room connections
        if chat_id:
            if chat_id not in self.chat_connections:
                self.chat_connections[chat_id] = set()
            self.chat_connections[chat_id].add(connection_id)
        
        logger.info(
            f"WebSocket connection established",
            extra={
                "connection_id": connection_id,
                "user_id": user_id,
                "chat_id": chat_id,
                "total_connections": len(self.active_connections)
            }
        )
        
        return connection_id
    
    async def disconnect(
        self, 
        connection_id: str, 
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None
    ) -> None:
        """
        Disconnect and cleanup WebSocket connection.
        
        Args:
            connection_id: Connection ID to disconnect
            user_id: Optional user ID for cleanup
            chat_id: Optional chat ID for cleanup
        """
        # Remove from active connections
        websocket = self.active_connections.pop(connection_id, None)
        
        # Cleanup user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Cleanup chat connections
        if chat_id and chat_id in self.chat_connections:
            self.chat_connections[chat_id].discard(connection_id)
            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]
        
        # Close connection if still open
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {str(e)}")
        
        logger.info(
            f"WebSocket connection closed",
            extra={
                "connection_id": connection_id,
                "user_id": user_id,
                "chat_id": chat_id,
                "total_connections": len(self.active_connections)
            }
        )
    
    async def send_personal_message(
        self, 
        message: str, 
        connection_id: str,
        correlation_id: str = ""
    ) -> bool:
        """
        Send message to specific connection.
        
        Args:
            message: Message to send
            connection_id: Target connection ID
            correlation_id: Request correlation ID for tracking
            
        Returns:
            True if message sent successfully, False otherwise
        """
        websocket = self.active_connections.get(connection_id)
        if not websocket:
            logger.warning(
                f"Connection not found for personal message",
                extra={"connection_id": connection_id, "correlation_id": correlation_id}
            )
            return False
        
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
                
                logger.debug(
                    f"Personal message sent",
                    extra={
                        "connection_id": connection_id,
                        "message_length": len(message),
                        "correlation_id": correlation_id
                    }
                )
                return True
            else:
                logger.warning(
                    f"WebSocket not connected for personal message",
                    extra={"connection_id": connection_id, "correlation_id": correlation_id}
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Failed to send personal message: {str(e)}",
                extra={"connection_id": connection_id, "correlation_id": correlation_id}
            )
            # Clean up broken connection
            await self.disconnect(connection_id)
            return False
    
    async def send_to_user(
        self, 
        message: str, 
        user_id: str,
        correlation_id: str = ""
    ) -> int:
        """
        Send message to all connections for a user.
        
        Args:
            message: Message to send
            user_id: Target user ID
            correlation_id: Request correlation ID for tracking
            
        Returns:
            Number of connections message was sent to
        """
        connection_ids = self.user_connections.get(user_id, set())
        sent_count = 0
        
        # Send to all user connections
        for connection_id in connection_ids.copy():  # Copy to avoid modification during iteration
            success = await self.send_personal_message(message, connection_id, correlation_id)
            if success:
                sent_count += 1
        
        logger.debug(
            f"Message sent to user connections",
            extra={
                "user_id": user_id,
                "connections_sent": sent_count,
                "total_connections": len(connection_ids),
                "correlation_id": correlation_id
            }
        )
        
        return sent_count
    
    async def send_to_chat(
        self, 
        message: str, 
        chat_id: str,
        exclude_connection: Optional[str] = None,
        correlation_id: str = ""
    ) -> int:
        """
        Send message to all connections in a chat room.
        
        Args:
            message: Message to send
            chat_id: Target chat room ID
            exclude_connection: Optional connection ID to exclude
            correlation_id: Request correlation ID for tracking
            
        Returns:
            Number of connections message was sent to
        """
        connection_ids = self.chat_connections.get(chat_id, set())
        sent_count = 0
        
        # Send to all chat connections except excluded
        for connection_id in connection_ids.copy():  # Copy to avoid modification during iteration
            if connection_id != exclude_connection:
                success = await self.send_personal_message(message, connection_id, correlation_id)
                if success:
                    sent_count += 1
        
        logger.debug(
            f"Message sent to chat connections",
            extra={
                "chat_id": chat_id,
                "connections_sent": sent_count,
                "total_connections": len(connection_ids),
                "excluded_connection": exclude_connection,
                "correlation_id": correlation_id
            }
        )
        
        return sent_count
    
    async def broadcast(self, message: str, correlation_id: str = "") -> int:
        """
        Broadcast message to all active connections.
        
        Args:
            message: Message to broadcast
            correlation_id: Request correlation ID for tracking
            
        Returns:
            Number of connections message was sent to
        """
        sent_count = 0
        
        # Send to all active connections
        for connection_id in list(self.active_connections.keys()):  # Copy to avoid modification
            success = await self.send_personal_message(message, connection_id, correlation_id)
            if success:
                sent_count += 1
        
        logger.info(
            f"Message broadcast completed",
            extra={
                "connections_sent": sent_count,
                "total_connections": len(self.active_connections),
                "correlation_id": correlation_id
            }
        )
        
        return sent_count
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for specific user."""
        return len(self.user_connections.get(user_id, set()))
    
    def get_chat_connection_count(self, chat_id: str) -> int:
        """Get number of connections in specific chat room."""
        return len(self.chat_connections.get(chat_id, set()))


# Global connection manager instance
connection_manager = ConnectionManager()


async def websocket_handler(
    websocket: WebSocket,
    user_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    correlation_id: str = ""
) -> None:
    """
    Handle WebSocket connection lifecycle and messages.
    
    Args:
        websocket: WebSocket connection
        user_id: Optional authenticated user ID
        chat_id: Optional chat room ID
        correlation_id: Request correlation ID for tracking
    """
    connection_id = await connection_manager.connect(websocket, user_id, chat_id)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")
                
                logger.debug(
                    f"WebSocket message received",
                    extra={
                        "connection_id": connection_id,
                        "message_type": message_type,
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "correlation_id": correlation_id
                    }
                )
                
                # Handle different message types
                if message_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
                elif message_type == "join_chat":
                    # Handle chat room joining
                    new_chat_id = message_data.get("chat_id")
                    if new_chat_id:
                        if chat_id and chat_id in connection_manager.chat_connections:
                            connection_manager.chat_connections[chat_id].discard(connection_id)
                        
                        if new_chat_id not in connection_manager.chat_connections:
                            connection_manager.chat_connections[new_chat_id] = set()
                        connection_manager.chat_connections[new_chat_id].add(connection_id)
                        
                        await websocket.send_text(json.dumps({
                            "type": "chat_joined",
                            "chat_id": new_chat_id
                        }))
                
                # Additional message types can be handled here
                
            except json.JSONDecodeError:
                logger.warning(
                    f"Invalid JSON received from WebSocket",
                    extra={"connection_id": connection_id, "correlation_id": correlation_id}
                )
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            
    except WebSocketDisconnect:
        logger.info(
            f"WebSocket disconnected",
            extra={"connection_id": connection_id, "correlation_id": correlation_id}
        )
    except Exception as e:
        logger.error(
            f"WebSocket error: {str(e)}",
            extra={"connection_id": connection_id, "correlation_id": correlation_id}
        )
    finally:
        await connection_manager.disconnect(connection_id, user_id, chat_id)