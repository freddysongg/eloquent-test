"""
WebSocket connection manager for real-time chat functionality.

Manages WebSocket connections, message broadcasting, and connection lifecycle
with proper error handling and connection cleanup.
"""

import json
import logging
import time
from typing import Any, Dict, Optional, Set
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

        # Performance monitoring
        self.connection_metrics: Dict[str, Dict[str, Any]] = {}
        self.last_ping_times: Dict[str, float] = {}
        self.message_counts: Dict[str, int] = {}

        # Health monitoring
        self.failed_send_count = 0
        self.total_send_count = 0
        self.connection_start_time = time.time()

        logger.info(
            "WebSocket connection manager initialized with performance monitoring"
        )

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None,
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

        # Initialize connection metrics
        self.connection_metrics[connection_id] = {
            "connected_at": time.time(),
            "user_id": user_id,
            "chat_id": chat_id,
            "messages_sent": 0,
            "messages_received": 0,
            "last_activity": time.time(),
            "ping_failures": 0,
        }
        self.message_counts[connection_id] = 0
        self.last_ping_times[connection_id] = time.time()

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
                "total_connections": len(self.active_connections),
            },
        )

        return connection_id

    async def disconnect(
        self,
        connection_id: str,
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None,
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

        # Cleanup metrics
        connection_metrics = self.connection_metrics.pop(connection_id, None)
        self.message_counts.pop(connection_id, None)
        self.last_ping_times.pop(connection_id, None)

        # Log connection duration for monitoring
        if connection_metrics:
            duration = time.time() - connection_metrics["connected_at"]
            logger.info(
                f"Connection duration metrics",
                extra={
                    "connection_id": connection_id,
                    "duration_seconds": round(duration, 2),
                    "messages_sent": connection_metrics["messages_sent"],
                    "messages_received": connection_metrics["messages_received"],
                    "ping_failures": connection_metrics["ping_failures"],
                },
            )

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
                "total_connections": len(self.active_connections),
            },
        )

    async def send_personal_message(
        self, message: str, connection_id: str, correlation_id: str = ""
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
                extra={
                    "connection_id": connection_id,
                    "correlation_id": correlation_id,
                },
            )
            return False

        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                # Update metrics before sending
                self.total_send_count += 1
                if connection_id in self.connection_metrics:
                    self.connection_metrics[connection_id]["messages_sent"] += 1
                    self.connection_metrics[connection_id][
                        "last_activity"
                    ] = time.time()

                await websocket.send_text(message)

                logger.debug(
                    f"Personal message sent",
                    extra={
                        "connection_id": connection_id,
                        "message_length": len(message),
                        "correlation_id": correlation_id,
                        "total_sent": self.total_send_count,
                    },
                )
                return True
            else:
                logger.warning(
                    f"WebSocket not connected for personal message",
                    extra={
                        "connection_id": connection_id,
                        "correlation_id": correlation_id,
                    },
                )
                return False

        except Exception as e:
            # Update failure metrics
            self.failed_send_count += 1
            if connection_id in self.connection_metrics:
                self.connection_metrics[connection_id]["ping_failures"] += 1

            logger.error(
                f"Failed to send personal message: {str(e)}",
                extra={
                    "connection_id": connection_id,
                    "correlation_id": correlation_id,
                    "failed_sends": self.failed_send_count,
                    "success_rate": round(
                        (self.total_send_count - self.failed_send_count)
                        / max(self.total_send_count, 1),
                        3,
                    ),
                },
            )
            # Clean up broken connection
            await self.disconnect(connection_id)
            return False

    async def send_to_user(
        self, message: str, user_id: str, correlation_id: str = ""
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
        for (
            connection_id
        ) in connection_ids.copy():  # Copy to avoid modification during iteration
            success = await self.send_personal_message(
                message, connection_id, correlation_id
            )
            if success:
                sent_count += 1

        logger.debug(
            f"Message sent to user connections",
            extra={
                "user_id": user_id,
                "connections_sent": sent_count,
                "total_connections": len(connection_ids),
                "correlation_id": correlation_id,
            },
        )

        return sent_count

    async def send_to_chat(
        self,
        message: str,
        chat_id: str,
        exclude_connection: Optional[str] = None,
        correlation_id: str = "",
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
        for (
            connection_id
        ) in connection_ids.copy():  # Copy to avoid modification during iteration
            if connection_id != exclude_connection:
                success = await self.send_personal_message(
                    message, connection_id, correlation_id
                )
                if success:
                    sent_count += 1

        logger.debug(
            f"Message sent to chat connections",
            extra={
                "chat_id": chat_id,
                "connections_sent": sent_count,
                "total_connections": len(connection_ids),
                "excluded_connection": exclude_connection,
                "correlation_id": correlation_id,
            },
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
        for connection_id in list(
            self.active_connections.keys()
        ):  # Copy to avoid modification
            success = await self.send_personal_message(
                message, connection_id, correlation_id
            )
            if success:
                sent_count += 1

        logger.info(
            f"Message broadcast completed",
            extra={
                "connections_sent": sent_count,
                "total_connections": len(self.active_connections),
                "correlation_id": correlation_id,
            },
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

    def get_connection_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics for all connections."""
        current_time = time.time()
        uptime = current_time - self.connection_start_time

        active_count = len(self.active_connections)
        healthy_connections = 0
        stale_connections = 0

        avg_duration = 0
        total_messages_sent = 0
        total_messages_received = 0

        for conn_id, metrics in self.connection_metrics.items():
            connection_age = current_time - metrics["connected_at"]
            last_activity_age = current_time - metrics["last_activity"]

            # Consider connection healthy if active within last 30 seconds
            if last_activity_age < 30:
                healthy_connections += 1
            elif last_activity_age > 300:  # 5 minutes
                stale_connections += 1

            avg_duration += connection_age
            total_messages_sent += metrics["messages_sent"]
            total_messages_received += metrics["messages_received"]

        if active_count > 0:
            avg_duration /= active_count

        success_rate = (self.total_send_count - self.failed_send_count) / max(
            self.total_send_count, 1
        )

        return {
            "websocket_health": {
                "uptime_seconds": round(uptime, 2),
                "total_connections": active_count,
                "healthy_connections": healthy_connections,
                "stale_connections": stale_connections,
                "user_connections": len(self.user_connections),
                "chat_connections": len(self.chat_connections),
                "avg_connection_duration": round(avg_duration, 2),
                "message_success_rate": round(success_rate, 3),
                "total_messages_sent": self.total_send_count,
                "failed_messages": self.failed_send_count,
                "messages_per_connection": round(
                    total_messages_sent / max(active_count, 1), 2
                ),
            }
        }

    async def optimize_streaming_delivery(
        self, message: str, connection_id: str, chunk_delay_ms: float = 8.0
    ) -> bool:
        """
        Send message with optimized chunking for smooth frontend rendering.

        Args:
            message: Message to send (typically streaming token)
            connection_id: Target connection ID
            chunk_delay_ms: Delay between chunks in milliseconds

        Returns:
            True if message sent successfully
        """
        websocket = self.active_connections.get(connection_id)
        if not websocket or websocket.client_state != WebSocketState.CONNECTED:
            return False

        try:
            # Parse JSON message to extract streaming content
            try:
                msg_data = json.loads(message)
                content = msg_data.get("content", "")

                # For streaming tokens, send immediately without additional chunking
                # The Claude client already handles token chunking
                if msg_data.get("type") == "token" and len(content) <= 10:
                    await websocket.send_text(message)

                    # Update metrics
                    if connection_id in self.connection_metrics:
                        self.connection_metrics[connection_id]["messages_sent"] += 1
                        self.connection_metrics[connection_id][
                            "last_activity"
                        ] = time.time()

                    return True
                else:
                    # For longer content, send as-is (status messages, etc.)
                    await websocket.send_text(message)

                    if connection_id in self.connection_metrics:
                        self.connection_metrics[connection_id]["messages_sent"] += 1
                        self.connection_metrics[connection_id][
                            "last_activity"
                        ] = time.time()

                    return True

            except json.JSONDecodeError:
                # Not JSON, send as plain text
                await websocket.send_text(message)

                if connection_id in self.connection_metrics:
                    self.connection_metrics[connection_id]["messages_sent"] += 1
                    self.connection_metrics[connection_id][
                        "last_activity"
                    ] = time.time()

                return True

        except Exception as e:
            logger.error(
                f"Optimized streaming delivery failed: {str(e)}",
                extra={"connection_id": connection_id},
            )
            return False

    async def cleanup_stale_connections(self, max_idle_minutes: int = 10) -> int:
        """Clean up connections that have been idle for too long."""
        current_time = time.time()
        stale_connections = []

        for conn_id, metrics in self.connection_metrics.items():
            last_activity = metrics["last_activity"]
            idle_time = (current_time - last_activity) / 60  # Convert to minutes

            if idle_time > max_idle_minutes:
                stale_connections.append(
                    (conn_id, metrics.get("user_id"), metrics.get("chat_id"))
                )

        # Clean up stale connections
        for conn_id, user_id, chat_id in stale_connections:
            logger.info(
                f"Cleaning up stale connection",
                extra={"connection_id": conn_id, "idle_minutes": idle_time},
            )
            await self.disconnect(conn_id, user_id, chat_id)

        return len(stale_connections)


# Global connection manager instance
connection_manager = ConnectionManager()


async def websocket_handler(
    websocket: WebSocket,
    user_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    correlation_id: str = "",
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
                        "correlation_id": correlation_id,
                    },
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
                            connection_manager.chat_connections[chat_id].discard(
                                connection_id
                            )

                        if new_chat_id not in connection_manager.chat_connections:
                            connection_manager.chat_connections[new_chat_id] = set()
                        connection_manager.chat_connections[new_chat_id].add(
                            connection_id
                        )

                        await websocket.send_text(
                            json.dumps({"type": "chat_joined", "chat_id": new_chat_id})
                        )

                # Additional message types can be handled here

            except json.JSONDecodeError:
                logger.warning(
                    f"Invalid JSON received from WebSocket",
                    extra={
                        "connection_id": connection_id,
                        "correlation_id": correlation_id,
                    },
                )
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON format"})
                )

    except WebSocketDisconnect:
        logger.info(
            f"WebSocket disconnected",
            extra={"connection_id": connection_id, "correlation_id": correlation_id},
        )
    except Exception as e:
        logger.error(
            f"WebSocket error: {str(e)}",
            extra={"connection_id": connection_id, "correlation_id": correlation_id},
        )
    finally:
        await connection_manager.disconnect(connection_id, user_id, chat_id)
