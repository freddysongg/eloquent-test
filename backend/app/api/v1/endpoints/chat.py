"""
Chat management endpoints with RAG-powered AI responses.

Handles chat CRUD operations and message streaming with real-time
Claude API integration, context retrieval from Pinecone, and comprehensive
error handling with resilience patterns for production stability.
"""

import json
import logging
import time
from typing import AsyncGenerator, Optional, Union
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.common import get_correlation_id
from app.core.monitoring import track_error, track_health_metrics
from app.core.resilience import resilience_manager
from app.core.websocket import connection_manager
from app.models.base import get_db_session
from app.models.user import User
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessageRequest(BaseModel):
    """Request schema for sending chat messages."""

    message: str
    stream: bool = True


class ChatResponse(BaseModel):
    """Response schema for chat operations."""

    chat_id: str
    message_id: str
    response: Optional[str] = None


@router.get("/")
async def list_chats(
    current_user: Optional[User] = Depends(get_current_user),
    correlation_id: str = Depends(get_correlation_id),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    List user's chat conversations.

    Args:
        current_user: Authenticated user (optional for anonymous)
        correlation_id: Request correlation ID
        db: Database session

    Returns:
        List of user's chat conversations
    """
    logger.info(
        "Listing chats",
        extra={
            "user_id": str(current_user.id) if current_user else "anonymous",
            "correlation_id": correlation_id,
        },
    )

    try:
        chat_service = ChatService(db)

        # Get chats for authenticated user or anonymous session
        if current_user:
            # Authenticated user - get their chats
            chats = await chat_service.chat_repository.list_by_user(
                user_id=current_user.id, limit=50, include_archived=False
            )
        else:
            # Anonymous user - get chats by session/correlation ID
            chats = await chat_service.chat_repository.list_by_session(
                session_id=correlation_id, limit=50, include_archived=False
            )

        # Convert chats to response format
        chat_data = []
        for chat in chats:
            chat_dict = chat.to_dict(exclude={"chat_metadata"}, include_messages=False)
            chat_data.append(chat_dict)

        return {"data": {"chats": chat_data, "total": len(chat_data)}, "error": None}

    except Exception as e:
        logger.error(
            f"Failed to list chats: {str(e)}", extra={"correlation_id": correlation_id}
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to retrieve chats",
                "code": "CHAT_LIST_ERROR",
                "correlation_id": correlation_id,
            },
        )


@router.post("/")
async def create_chat(
    current_user: Optional[User] = Depends(get_current_user),
    correlation_id: str = Depends(get_correlation_id),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Create new chat conversation.

    Args:
        current_user: Authenticated user (optional for anonymous)
        correlation_id: Request correlation ID
        db: Database session

    Returns:
        New chat conversation details
    """
    logger.info(
        f"Creating new chat",
        extra={
            "user_id": str(current_user.id) if current_user else "anonymous",
            "correlation_id": correlation_id,
        },
    )

    try:
        chat_service = ChatService(db)

        # Create chat with default title
        title = "New Chat"
        user_id = current_user.id if current_user else None
        session_id = correlation_id if not current_user else None

        chat = await chat_service.create_chat(
            title=title,
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id,
        )

        return {
            "data": {
                "chat_id": str(chat.id),
                "title": chat.title,
                "created_at": chat.created_at.isoformat(),
            },
            "error": None,
        }

    except Exception as e:
        logger.error(
            f"Failed to create chat: {str(e)}", extra={"correlation_id": correlation_id}
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to create chat",
                "code": "CHAT_CREATE_ERROR",
                "correlation_id": correlation_id,
            },
        )


@router.get("/{chat_id}")
async def get_chat(
    chat_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    correlation_id: str = Depends(get_correlation_id),
    db: AsyncSession = Depends(get_db_session),
    include_rag_metadata: bool = False,
) -> dict:
    """
    Get specific chat conversation with message history.

    Args:
        chat_id: Chat conversation ID
        current_user: Authenticated user (optional for anonymous)
        correlation_id: Request correlation ID
        db: Database session
        include_rag_metadata: Whether to include RAG context in response

    Returns:
        Chat conversation details and message history
    """
    logger.info(
        f"Getting chat",
        extra={
            "chat_id": chat_id,
            "user_id": str(current_user.id) if current_user else "anonymous",
            "correlation_id": correlation_id,
            "include_rag_metadata": include_rag_metadata,
        },
    )

    try:
        chat_service = ChatService(db)
        chat_uuid = UUID(chat_id)

        # Get chat history
        messages = await chat_service.get_chat_history(
            chat_id=chat_uuid,
            limit=100,
            include_rag_metadata=include_rag_metadata,
            correlation_id=correlation_id,
        )

        # Convert messages to response format
        message_data = []
        for msg in messages:
            msg_dict = msg.to_dict(include_rag_context=include_rag_metadata)
            message_data.append(msg_dict)

        return {
            "data": {
                "chat_id": chat_id,
                "messages": message_data,
                "message_count": len(messages),
                "rag_messages_count": sum(1 for msg in messages if msg.has_rag_context),
            },
            "error": None,
        }

    except ValueError as e:
        logger.error(
            f"Invalid chat ID format: {str(e)}",
            extra={"correlation_id": correlation_id},
        )

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid chat ID format",
                "code": "INVALID_CHAT_ID",
                "correlation_id": correlation_id,
            },
        )

    except Exception as e:
        logger.error(
            f"Failed to get chat: {str(e)}",
            extra={"correlation_id": correlation_id, "chat_id": chat_id},
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to retrieve chat",
                "code": "CHAT_GET_ERROR",
                "correlation_id": correlation_id,
            },
        )


@router.post("/{chat_id}/messages", response_model=None)
async def send_message(
    chat_id: str,
    request: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user),
    correlation_id: str = Depends(get_correlation_id),
    db: AsyncSession = Depends(get_db_session),
) -> Union[StreamingResponse, JSONResponse]:
    """
    Send message to chat conversation with RAG-powered AI response.

    Args:
        chat_id: Chat conversation ID
        request: Message request with content and streaming preference
        background_tasks: Background task manager for async operations
        current_user: Authenticated user (optional for anonymous)
        correlation_id: Request correlation ID
        db: Database session

    Returns:
        Streaming AI response with RAG integration
    """
    message_id = str(uuid4())
    user_id_str = str(current_user.id) if current_user else "anonymous"

    logger.info(
        f"Processing chat message with RAG integration",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
            "user_id": user_id_str,
            "message_length": len(request.message),
            "stream": request.stream,
            "correlation_id": correlation_id,
        },
    )

    try:
        chat_service = ChatService(db)
        chat_uuid = UUID(chat_id)

        if request.stream:
            # Stream response with RAG integration and error resilience
            async def stream_generator() -> AsyncGenerator[str, None]:
                start_time = time.time()
                tokens_streamed = 0
                streaming_errors = 0

                try:
                    rag_metadata = {}

                    # Process message through ChatService with full RAG pipeline
                    async for chunk in chat_service.process_message(
                        chat_id=chat_uuid,
                        message_content=request.message,
                        user=current_user,
                        correlation_id=correlation_id,
                    ):
                        try:
                            # Extract metadata for final response
                            if chunk.get("type") == "complete" and chunk.get(
                                "metadata"
                            ):
                                rag_metadata = chunk["metadata"]

                            # Send chunk to WebSocket connections with error handling
                            if (
                                connection_manager.get_chat_connection_count(chat_id)
                                > 0
                            ):
                                try:
                                    # Convert chunk dict to JSON string for WebSocket transmission
                                    chunk_json = (
                                        json.dumps(chunk)
                                        if isinstance(chunk, dict)
                                        else str(chunk)
                                    )
                                    await connection_manager.send_to_chat(
                                        chunk_json,
                                        chat_id,
                                        correlation_id=correlation_id,
                                    )
                                except Exception as ws_error:
                                    logger.warning(
                                        f"WebSocket send failed: {str(ws_error)}",
                                        extra={
                                            "chat_id": chat_id,
                                            "correlation_id": correlation_id,
                                        },
                                    )
                                    track_error(
                                        "websocket",
                                        "send_failure",
                                        str(ws_error),
                                        correlation_id,
                                        chat_id=chat_id,
                                    )

                            # Format chunk for HTTP streaming
                            chunk_data = {
                                "type": chunk.get("type", "token"),
                                "content": chunk.get("content", ""),
                                "step": chunk.get("step"),
                            }

                            # Include metadata in appropriate chunks
                            if chunk.get("metadata"):
                                chunk_data["metadata"] = chunk["metadata"]

                            # Track streaming metrics
                            if chunk.get("type") == "token":
                                tokens_streamed += 1

                            yield f"data: {chunk_data}\n\n"

                        except Exception as chunk_error:
                            streaming_errors += 1
                            logger.warning(
                                f"Error processing stream chunk: {str(chunk_error)}",
                                extra={
                                    "chat_id": chat_id,
                                    "correlation_id": correlation_id,
                                    "chunk_type": chunk.get("type", "unknown"),
                                },
                            )

                            # Continue streaming despite chunk errors
                            if streaming_errors > 10:  # Too many errors, stop streaming
                                break

                    # Send final completion with metadata
                    final_chunk = {
                        "type": "done",
                        "content": "",
                        "metadata": rag_metadata,
                    }
                    yield f"data: {final_chunk}\n\n"

                    # Track successful streaming metrics
                    duration = time.time() - start_time
                    track_health_metrics(
                        "chat_streaming",
                        "healthy",
                        duration * 1000,  # Convert to milliseconds
                        streaming_errors / max(tokens_streamed, 1),
                        60.0,  # Rough RPM estimate
                        "closed",  # Streaming doesn't use circuit breaker directly
                        tokens_streamed=tokens_streamed,
                        streaming_errors=streaming_errors,
                    )

                except Exception as e:
                    logger.error(
                        f"Critical streaming error: {str(e)}",
                        extra={
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "correlation_id": correlation_id,
                            "tokens_streamed": tokens_streamed,
                            "streaming_errors": streaming_errors,
                        },
                    )

                    track_error(
                        "chat_streaming",
                        type(e).__name__,
                        str(e),
                        correlation_id,
                        chat_id=chat_id,
                        message_id=message_id,
                        tokens_streamed=tokens_streamed,
                    )

                    # Attempt graceful error recovery
                    try:
                        error_chunk = {
                            "type": "error",
                            "content": "I'm experiencing technical difficulties. Please try again.",
                            "step": "error",
                            "recoverable": True,
                        }
                        yield f"data: {error_chunk}\n\n"

                        # Send service health information
                        health_chunk = {
                            "type": "system_status",
                            "content": "",
                            "metadata": {
                                "service_health": resilience_manager.get_overall_health(),
                                "suggested_action": "retry_in_moments",
                            },
                        }
                        yield f"data: {health_chunk}\n\n"

                    except Exception as recovery_error:
                        logger.error(
                            f"Error recovery failed: {str(recovery_error)}",
                            extra={"correlation_id": correlation_id},
                        )

            return StreamingResponse(
                stream_generator(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "X-Correlation-ID": correlation_id,
                    "X-Message-ID": message_id,
                },
            )

        else:
            # Non-streaming response using get_rag_response interface
            try:
                # Get chat history for context
                messages = await chat_service.get_chat_history(
                    chat_id=chat_uuid, limit=10, correlation_id=correlation_id
                )

                # Get RAG-enhanced response
                response_text, rag_metadata = await chat_service.get_rag_response(
                    message=request.message,
                    history=messages,
                    user_id=user_id_str,
                    correlation_id=correlation_id,
                )

                # Save user message and AI response (done within get_rag_response for streaming,
                # but we need to do it manually for non-streaming)
                # TODO: Implement non-streaming message persistence

                response_data = {
                    "data": {
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "response": response_text,
                        "rag_metadata": rag_metadata,
                    },
                    "error": None,
                }

                return JSONResponse(content=response_data)

            except Exception as e:
                logger.error(
                    f"Non-streaming message processing failed: {str(e)}",
                    extra={"chat_id": chat_id, "correlation_id": correlation_id},
                )
                raise

    except ValueError as e:
        logger.error(
            f"Invalid chat ID format: {str(e)}",
            extra={"correlation_id": correlation_id},
        )

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid chat ID format",
                "code": "INVALID_CHAT_ID",
                "correlation_id": correlation_id,
            },
        )

    except Exception as e:
        logger.error(
            f"Chat message processing failed: {str(e)}",
            extra={
                "chat_id": chat_id,
                "message_id": message_id,
                "correlation_id": correlation_id,
            },
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to process message",
                "code": "MESSAGE_PROCESSING_ERROR",
                "correlation_id": correlation_id,
            },
        )


@router.get("/health")
async def health_check(
    correlation_id: str = Depends(get_correlation_id),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Comprehensive health check endpoint for chat service and RAG integration.

    Includes circuit breaker status, error monitoring, and service resilience metrics.

    Args:
        correlation_id: Request correlation ID
        db: Database session

    Returns:
        Detailed health status of all chat service components with resilience metrics
    """
    logger.info(
        f"Performing comprehensive chat service health check",
        extra={"correlation_id": correlation_id},
    )

    start_time = time.time()
    health_data = {
        "service": "chat_service",
        "status": "healthy",
        "timestamp": start_time,
        "checks": {},
        "resilience": {},
        "monitoring": {},
    }

    try:
        # Basic chat service health check
        chat_service = ChatService(db)
        chat_health = await chat_service.health_check(correlation_id)
        if isinstance(health_data["checks"], dict):
            health_data["checks"]["chat_service"] = chat_health

        # Circuit breaker status
        try:
            overall_resilience = resilience_manager.get_overall_health()
            health_data["resilience"] = {
                "overall_status": overall_resilience["overall_status"],
                "healthy_services": overall_resilience["healthy_services"],
                "total_services": overall_resilience["total_services"],
                "circuit_breakers": {
                    service: {
                        "state": details["state"],
                        "status": details["status"],
                        "error_rate": details["error_rate"],
                        "total_requests": details["total_requests"],
                    }
                    for service, details in overall_resilience["services"].items()
                },
            }

            # Determine overall status based on resilience
            if overall_resilience["overall_status"] == "unhealthy":
                health_data["status"] = "unhealthy"
            elif overall_resilience["overall_status"] == "degraded":
                health_data["status"] = "degraded"

        except Exception as resilience_error:
            logger.warning(
                f"Failed to get resilience status: {str(resilience_error)}",
                extra={"correlation_id": correlation_id},
            )
            health_data["resilience"] = {"error": str(resilience_error)}

        # Error monitoring status
        try:
            from app.core.monitoring import error_monitor

            error_summary = error_monitor.get_error_summary(15)  # Last 15 minutes
            system_dashboard = error_monitor.get_system_health_dashboard()

            health_data["monitoring"] = {
                "errors_last_15min": error_summary["total_errors"],
                "unique_error_types": error_summary["unique_error_types"],
                "services_affected": error_summary["services_affected"],
                "active_alerts": system_dashboard["alerts"]["active_alerts"],
                "alert_rules_enabled": system_dashboard["alerts"]["enabled_rules"],
                "top_errors": error_summary["top_errors"][:3],  # Top 3 errors
            }

            # Adjust status based on error rates
            if error_summary["total_errors"] > 50:  # High error count
                if health_data["status"] == "healthy":
                    health_data["status"] = "degraded"

            if system_dashboard["alerts"]["active_alerts"] > 0:
                health_data["status"] = "degraded"

        except Exception as monitoring_error:
            logger.warning(
                f"Failed to get monitoring status: {str(monitoring_error)}",
                extra={"correlation_id": correlation_id},
            )
            health_data["monitoring"] = {"error": str(monitoring_error)}

        # Performance metrics
        duration = time.time() - start_time
        health_data["performance"] = {
            "health_check_duration_ms": round(duration * 1000, 2),
            "response_under_1s": duration < 1.0,
        }

        # Track health check metrics
        track_health_metrics(
            "chat_health_check",
            str(health_data["status"]),
            duration * 1000,
            0.0,  # No errors in successful health check
            4.0,  # Roughly once per 15 seconds
            "closed",
        )

        logger.info(
            f"Health check completed successfully",
            extra={
                "correlation_id": correlation_id,
                "overall_status": health_data["status"],
                "duration_ms": round(duration * 1000, 2),
                "active_alerts": (
                    monitoring_data.get("active_alerts", 0)
                    if (monitoring_data := health_data.get("monitoring"))
                    and isinstance(monitoring_data, dict)
                    else 0
                ),
            },
        )

        return {"data": health_data, "error": None}

    except Exception as e:
        duration = time.time() - start_time

        logger.error(
            f"Health check failed: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(duration * 1000, 2),
            },
        )

        # Track health check failure
        track_error(
            "chat_health_check",
            type(e).__name__,
            str(e),
            correlation_id,
            duration_ms=round(duration * 1000, 2),
        )

        error_health_data = {
            "service": "chat_service",
            "status": "unhealthy",
            "timestamp": start_time,
            "error": str(e),
            "performance": {
                "health_check_duration_ms": round(duration * 1000, 2),
            },
        }

        return {
            "data": error_health_data,
            "error": {
                "message": "Health check failed",
                "code": "HEALTH_CHECK_ERROR",
                "correlation_id": correlation_id,
            },
        }


@router.get("/system/status")
async def system_status(
    correlation_id: str = Depends(get_correlation_id),
) -> dict:
    """
    Get comprehensive system status including circuit breakers and error monitoring.

    Provides detailed operational metrics for debugging and monitoring.
    """
    try:
        from app.core.monitoring import error_monitor

        # Get comprehensive system health dashboard
        dashboard_data = error_monitor.get_system_health_dashboard()

        return {
            "data": {
                **dashboard_data,
                "correlation_id": correlation_id,
            },
            "error": None,
        }

    except Exception as e:
        logger.error(
            f"System status check failed: {str(e)}",
            extra={"correlation_id": correlation_id},
        )

        return {
            "data": None,
            "error": {
                "message": "Failed to retrieve system status",
                "code": "SYSTEM_STATUS_ERROR",
                "correlation_id": correlation_id,
            },
        }


@router.post("/system/circuit-breaker/{service_name}/reset")
async def reset_circuit_breaker(
    service_name: str,
    correlation_id: str = Depends(get_correlation_id),
) -> dict:
    """
    Reset a circuit breaker for a specific service (ops/admin endpoint).

    Args:
        service_name: Name of service circuit breaker to reset
        correlation_id: Request correlation ID
    """
    try:
        from app.core.resilience import CircuitState

        # Force circuit breaker to closed state
        resilience_manager.force_circuit_state(
            service_name,
            CircuitState.CLOSED,
            f"Manual reset via API - correlation_id: {correlation_id}",
        )

        logger.info(
            f"Circuit breaker reset for {service_name}",
            extra={
                "service_name": service_name,
                "correlation_id": correlation_id,
                "action": "manual_reset",
            },
        )

        return {
            "data": {
                "service_name": service_name,
                "action": "reset",
                "new_state": "closed",
                "correlation_id": correlation_id,
            },
            "error": None,
        }

    except Exception as e:
        logger.error(
            f"Circuit breaker reset failed for {service_name}: {str(e)}",
            extra={"correlation_id": correlation_id, "service_name": service_name},
        )

        return {
            "data": None,
            "error": {
                "message": f"Failed to reset circuit breaker for {service_name}",
                "code": "CIRCUIT_BREAKER_RESET_ERROR",
                "correlation_id": correlation_id,
            },
        }
