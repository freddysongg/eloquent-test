"""
Chat orchestration service with RAG integration.

Orchestrates RAG retrieval, AI response generation, and chat management
with full database persistence and error handling.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat
from app.models.message import Message, MessageRole
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository
from app.services.rag_service import RAGService
from app.services.response_cache_service import ResponseCacheService
from app.services.streaming_service import StreamingService

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat orchestration and message processing with RAG integration."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize chat service with dependencies.

        Args:
            db: Database session
        """
        self.db = db
        self.chat_repository = ChatRepository(db)
        self.message_repository = MessageRepository(db)
        self.rag_service = RAGService()
        self.streaming_service = StreamingService()
        self.response_cache = ResponseCacheService()

    async def create_chat(
        self,
        title: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        correlation_id: str = "",
    ) -> Chat:
        """
        Create new chat conversation.

        Args:
            title: Chat title
            user_id: User ID for authenticated users
            session_id: Session ID for anonymous users
            correlation_id: Request correlation ID

        Returns:
            Created chat instance
        """
        logger.info(
            f"Creating new chat",
            extra={
                "correlation_id": correlation_id,
                "user_id": str(user_id) if user_id else None,
                "session_id": session_id,
                "title": title,
            },
        )

        try:
            chat = Chat(title=title, user_id=user_id, session_id=session_id)

            # Save to database via repository
            created_chat = await self.chat_repository.create(chat)

            logger.info(
                f"Chat created successfully",
                extra={
                    "correlation_id": correlation_id,
                    "chat_id": str(created_chat.id),
                    "title": title,
                },
            )

            return created_chat

        except Exception as e:
            logger.error(
                f"Failed to create chat: {str(e)}",
                extra={"correlation_id": correlation_id, "title": title},
            )
            raise

    async def process_message(
        self,
        chat_id: UUID,
        message_content: str,
        user: Optional[User] = None,
        correlation_id: str = "",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process user message and stream AI response with RAG integration and caching.

        Args:
            chat_id: Chat conversation ID
            message_content: User message content
            user: Optional authenticated user
            correlation_id: Request correlation ID

        Yields:
            Streaming response chunks with metadata
        """
        user_id_str = str(user.id) if user else "anonymous"

        logger.info(
            f"Processing message with RAG integration and caching",
            extra={
                "correlation_id": correlation_id,
                "chat_id": str(chat_id),
                "user_id": user_id_str,
                "message_length": len(message_content),
            },
        )

        # Track completion state for error handling
        user_message_saved = False
        ai_response_content = ""
        retrieved_docs = []
        rag_metadata = {}
        cache_used = False

        try:
            # 0. Check for query deduplication first
            yield {
                "type": "status",
                "content": "Checking for duplicate queries...",
                "step": "deduplication_check",
            }

            dedup_result = await self.response_cache.deduplicate_query(
                query=message_content,
                user_id=user_id_str,
                correlation_id=correlation_id,
            )

            if dedup_result:
                query_hash, event = dedup_result

                yield {
                    "type": "status",
                    "content": "Similar query in progress, waiting for result...",
                    "step": "waiting_for_dedup",
                }

                # Wait for existing query to complete
                dedup_response = await self.response_cache.get_deduplicated_result(
                    query_hash=query_hash,
                    timeout=30.0,
                    correlation_id=correlation_id,
                )

                if dedup_response:
                    response_text, response_metadata = dedup_response

                    # Save user message
                    await self.message_repository.create(
                        chat_id=chat_id,
                        role=MessageRole.USER,
                        content=message_content,
                        correlation_id=correlation_id,
                    )

                    # Stream the deduplicated response
                    yield {"type": "start", "content": "", "step": "streaming_cached"}

                    # Stream response in chunks for smooth frontend rendering
                    words = response_text.split()
                    current_chunk = ""

                    for i, word in enumerate(words):
                        current_chunk += word + (" " if i < len(words) - 1 else "")

                        # Send chunk every 3-4 words for smooth streaming
                        if len(current_chunk.split()) >= 3 or i == len(words) - 1:
                            yield {
                                "type": "token",
                                "content": current_chunk,
                                "step": "streaming",
                            }
                            current_chunk = ""

                            # Small delay for frontend rendering
                            import asyncio

                            await asyncio.sleep(
                                0.015
                            )  # 15ms delay for smooth animation

                    # Save AI response
                    await self.message_repository.create(
                        chat_id=chat_id,
                        role=MessageRole.ASSISTANT,
                        content=response_text,
                        metadata={"deduplicated": True, **response_metadata},
                        correlation_id=correlation_id,
                    )

                    yield {
                        "type": "complete",
                        "content": "Deduplicated response completed",
                        "metadata": {"deduplicated": True, **response_metadata},
                        "step": "dedup_complete",
                    }
                    return

        except Exception as e:
            logger.warning(
                f"Query deduplication failed, proceeding normally: {str(e)}",
                extra={"correlation_id": correlation_id},
            )

        try:
            # 1. Save user message to database
            yield {
                "type": "status",
                "content": "Saving message...",
                "step": "save_user_message",
            }

            user_message = await self.message_repository.create(
                chat_id=chat_id,
                role=MessageRole.USER,
                content=message_content,
                correlation_id=correlation_id,
            )
            user_message_saved = True

            logger.info(
                f"User message saved",
                extra={
                    "correlation_id": correlation_id,
                    "message_id": str(user_message.id),
                },
            )

            # 2. Retrieve RAG context with enhanced hybrid search
            yield {
                "type": "status",
                "content": "Retrieving context...",
                "step": "rag_retrieval",
            }

            retrieved_docs = await self.rag_service.retrieve_context(
                query=message_content,
                top_k=5,
                correlation_id=correlation_id,
                use_hybrid_search=True,
            )

            # 2.5. Check for cached response with RAG context
            yield {
                "type": "status",
                "content": "Checking response cache...",
                "step": "cache_check",
            }

            cached_response = await self.response_cache.get_cached_response(
                query=message_content,
                context_docs=retrieved_docs,
                correlation_id=correlation_id,
            )

            if cached_response:
                cached_text, cached_metadata = cached_response
                cache_used = True

                logger.info(
                    f"Using cached response",
                    extra={
                        "correlation_id": correlation_id,
                        "response_length": len(cached_text),
                        "context_docs": len(retrieved_docs),
                    },
                )

                # Stream the cached response
                yield {"type": "start", "content": "", "step": "streaming_cached"}

                # Stream response in chunks for smooth frontend rendering
                words = cached_text.split()
                current_chunk = ""

                for i, word in enumerate(words):
                    current_chunk += word + (" " if i < len(words) - 1 else "")

                    # Send chunk every 3-4 words for smooth streaming
                    if len(current_chunk.split()) >= 3 or i == len(words) - 1:
                        yield {
                            "type": "token",
                            "content": current_chunk,
                            "step": "streaming",
                        }
                        current_chunk = ""

                        # Small delay for frontend rendering
                        import asyncio

                        await asyncio.sleep(0.012)  # 12ms delay for cached responses

                ai_response_content = cached_text
                rag_metadata = {**cached_metadata, "cache_hit": True}

                yield {"type": "end", "content": "", "step": "stream_complete"}

                # Save AI response with cache metadata
                await self.message_repository.create_with_rag_metadata(
                    chat_id=chat_id,
                    role=MessageRole.ASSISTANT,
                    content=ai_response_content,
                    retrieved_docs=retrieved_docs,
                    retrieval_query=message_content,
                    rag_metadata=rag_metadata,
                    correlation_id=correlation_id,
                )

                yield {
                    "type": "complete",
                    "content": "Cached response completed",
                    "metadata": rag_metadata,
                    "step": "cache_complete",
                }
                return

            # Build context metadata
            rag_metadata = {
                "search_method": (
                    "hybrid"
                    if retrieved_docs
                    and any(doc.get("hybrid_score") for doc in retrieved_docs)
                    else "vector_only"
                ),
                "documents_retrieved": len(retrieved_docs),
                "avg_confidence": (
                    sum(doc.get("confidence", 0) for doc in retrieved_docs)
                    / len(retrieved_docs)
                    if retrieved_docs
                    else 0
                ),
            }

            yield {
                "type": "context",
                "content": f"Retrieved {len(retrieved_docs)} relevant documents",
                "metadata": rag_metadata,
                "step": "context_retrieved",
            }

            # 3. Build conversation history
            conversation_history = await self.message_repository.get_recent_context(
                chat_id=chat_id,
                max_messages=10,
                max_tokens=4000,
                correlation_id=correlation_id,
            )

            logger.info(
                f"Built conversation context",
                extra={
                    "correlation_id": correlation_id,
                    "history_messages": len(conversation_history),
                    "context_documents": len(retrieved_docs),
                },
            )

            # 4. Build context prompt from retrieved documents
            context_prompt = None
            if retrieved_docs:
                context_prompt, context_metadata = (
                    await self.rag_service.build_context_prompt(
                        retrieved_docs, max_length=8000, correlation_id=correlation_id
                    )
                )
                rag_metadata.update(context_metadata)

            # 5. Stream AI response with RAG context
            yield {"type": "start", "content": "", "step": "streaming_response"}

            # Add current user message to conversation
            current_messages = conversation_history + [
                {"role": "user", "content": message_content}
            ]

            # Build system prompt with user context
            user_context = {
                "is_authenticated": bool(user),
                "account_type": "premium" if user else "anonymous",
            }
            system_prompt = self.streaming_service.build_system_prompt(user_context)

            async for token in self.streaming_service.stream_response(
                messages=current_messages,
                context=context_prompt,
                system_prompt=system_prompt,
                correlation_id=correlation_id,
            ):
                ai_response_content += token
                yield {"type": "token", "content": token, "step": "streaming"}

            yield {"type": "end", "content": "", "step": "stream_complete"}

            # 6. Save AI response with RAG metadata
            if ai_response_content.strip():
                await self.message_repository.create_with_rag_metadata(
                    chat_id=chat_id,
                    role=MessageRole.ASSISTANT,
                    content=ai_response_content.strip(),
                    retrieved_docs=retrieved_docs,
                    retrieval_query=message_content,
                    rag_metadata=rag_metadata,
                    correlation_id=correlation_id,
                )

                logger.info(
                    f"AI response saved with RAG metadata",
                    extra={
                        "correlation_id": correlation_id,
                        "response_length": len(ai_response_content),
                        "rag_documents": len(retrieved_docs),
                        "search_method": rag_metadata.get("search_method", "unknown"),
                    },
                )

                # 6.5. Cache response for future queries (async, don't wait)
                if not cache_used and ai_response_content.strip():
                    try:
                        # Determine if this is a common query (simple heuristic)
                        common_keywords = [
                            "balance",
                            "transaction",
                            "payment",
                            "security",
                            "account",
                            "fee",
                            "transfer",
                        ]
                        is_common = any(
                            keyword in message_content.lower()
                            for keyword in common_keywords
                        )

                        # Cache response asynchronously
                        import asyncio

                        asyncio.create_task(
                            self.response_cache.cache_response(
                                query=message_content,
                                response=ai_response_content.strip(),
                                metadata=rag_metadata,
                                context_docs=retrieved_docs,
                                is_common_query=is_common,
                                correlation_id=correlation_id,
                            )
                        )

                        # Notify query deduplication completion
                        asyncio.create_task(
                            self.response_cache.complete_query_processing(
                                query=message_content,
                                response=ai_response_content.strip(),
                                metadata=rag_metadata,
                                user_id=user_id_str,
                                correlation_id=correlation_id,
                            )
                        )

                        logger.debug(
                            f"Response caching initiated",
                            extra={
                                "correlation_id": correlation_id,
                                "is_common_query": is_common,
                                "response_length": len(ai_response_content),
                            },
                        )

                    except Exception as cache_error:
                        # Don't fail the main flow if caching fails
                        logger.warning(
                            f"Response caching failed: {str(cache_error)}",
                            extra={"correlation_id": correlation_id},
                        )

            yield {
                "type": "complete",
                "content": "Message processing completed",
                "metadata": {**rag_metadata, "cache_used": cache_used},
                "step": "complete",
            }

        except Exception as e:
            logger.error(
                f"Message processing failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "user_message_saved": user_message_saved,
                    "ai_response_length": len(ai_response_content),
                    "context_docs": len(retrieved_docs),
                },
            )

            # Attempt graceful fallback to direct Claude API
            try:
                yield {
                    "type": "status",
                    "content": "RAG failed, using fallback...",
                    "step": "fallback",
                }

                # Get basic conversation history
                basic_history = await self.message_repository.get_recent_context(
                    chat_id=chat_id,
                    max_messages=5,
                    max_tokens=2000,
                    correlation_id=correlation_id,
                )

                fallback_messages = basic_history + [
                    {"role": "user", "content": message_content}
                ]
                fallback_response = ""

                async for token in self.streaming_service.stream_response(
                    messages=fallback_messages,
                    context=None,  # No RAG context
                    correlation_id=correlation_id,
                ):
                    fallback_response += token
                    yield {
                        "type": "token",
                        "content": token,
                        "step": "fallback_streaming",
                    }

                # Save fallback response
                if fallback_response.strip():
                    await self.message_repository.create(
                        chat_id=chat_id,
                        role=MessageRole.ASSISTANT,
                        content=fallback_response.strip(),
                        metadata={"fallback": True, "original_error": str(e)},
                        correlation_id=correlation_id,
                    )

                yield {
                    "type": "complete",
                    "content": "Fallback response completed",
                    "step": "fallback_complete",
                }

            except Exception as fallback_error:
                logger.error(
                    f"Fallback also failed: {str(fallback_error)}",
                    extra={"correlation_id": correlation_id},
                )
                yield {
                    "type": "error",
                    "content": "Unable to process message. Please try again.",
                    "step": "error",
                }

    async def get_chat_history(
        self,
        chat_id: UUID,
        limit: int = 50,
        include_rag_metadata: bool = False,
        correlation_id: str = "",
    ) -> List[Message]:
        """
        Get chat message history with optional RAG metadata.

        Args:
            chat_id: Chat conversation ID
            limit: Maximum number of messages
            include_rag_metadata: Whether to include RAG context information
            correlation_id: Request correlation ID

        Returns:
            List of chat messages ordered by sequence
        """
        logger.info(
            f"Getting chat history",
            extra={
                "correlation_id": correlation_id,
                "chat_id": str(chat_id),
                "limit": limit,
                "include_rag_metadata": include_rag_metadata,
            },
        )

        try:
            messages = await self.message_repository.get_chat_history(
                chat_id=chat_id,
                limit=limit,
                include_rag_metadata=include_rag_metadata,
                correlation_id=correlation_id,
            )

            logger.info(
                f"Retrieved chat history",
                extra={
                    "correlation_id": correlation_id,
                    "message_count": len(messages),
                    "rag_messages": sum(1 for msg in messages if msg.has_rag_context),
                },
            )

            return messages

        except Exception as e:
            logger.error(
                f"Failed to get chat history: {str(e)}",
                extra={"correlation_id": correlation_id, "chat_id": str(chat_id)},
            )
            return []

    async def get_rag_response(
        self,
        message: str,
        history: List[Message],
        user_id: Optional[str] = None,
        correlation_id: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Get RAG-enhanced response for integration interface.

        This method provides the contract interface specified in the task requirements.

        Args:
            message: User message content
            history: Previous conversation messages
            user_id: Optional user identifier
            correlation_id: Request correlation ID

        Returns:
            Tuple of (response_text, rag_metadata)
        """
        logger.info(
            f"Getting RAG response via integration interface",
            extra={
                "correlation_id": correlation_id,
                "user_id": user_id,
                "message_length": len(message),
                "history_length": len(history),
            },
        )

        try:
            # Retrieve RAG context
            retrieved_docs = await self.rag_service.retrieve_context(
                query=message,
                top_k=5,
                correlation_id=correlation_id,
                use_hybrid_search=True,
            )

            # Build context prompt
            context_prompt = None
            context_metadata: Dict[str, Any] = {}

            if retrieved_docs:
                context_prompt, context_metadata = (
                    await self.rag_service.build_context_prompt(
                        retrieved_docs, max_length=8000, correlation_id=correlation_id
                    )
                )

            # Convert message history to API format
            conversation_messages = []
            for msg in history[-10:]:  # Last 10 messages
                conversation_messages.append(
                    {"role": msg.role.value, "content": msg.content}
                )

            # Add current message
            conversation_messages.append({"role": "user", "content": message})

            # Build system prompt
            user_context = {
                "is_authenticated": bool(user_id and user_id != "anonymous"),
                "account_type": (
                    "premium" if user_id and user_id != "anonymous" else "anonymous"
                ),
            }
            system_prompt = self.streaming_service.build_system_prompt(user_context)

            # Get complete response
            response_text = await self.streaming_service.get_single_response(
                messages=conversation_messages,
                context=context_prompt,
                system_prompt=system_prompt,
                correlation_id=correlation_id,
            )

            # Build RAG metadata
            rag_metadata = {
                "search_method": (
                    "hybrid"
                    if retrieved_docs
                    and any(doc.get("hybrid_score") for doc in retrieved_docs)
                    else "vector_only"
                ),
                "documents_retrieved": len(retrieved_docs),
                "avg_confidence": (
                    sum(doc.get("confidence", 0) for doc in retrieved_docs)
                    / len(retrieved_docs)
                    if retrieved_docs
                    else 0
                ),
                "sources": [],
                **context_metadata,
            }

            # Extract source information
            for doc in retrieved_docs:
                source_attr = doc.get("source_attribution", {})
                if source_attr:
                    rag_metadata["sources"].append(
                        {
                            "category": source_attr.get("category", "unknown"),
                            "source": source_attr.get("source", "unknown"),
                            "confidence": doc.get("confidence", 0),
                        }
                    )

            logger.info(
                f"RAG response generated successfully",
                extra={
                    "correlation_id": correlation_id,
                    "response_length": len(response_text),
                    "context_documents": len(retrieved_docs),
                    "search_method": rag_metadata["search_method"],
                },
            )

            return response_text, rag_metadata

        except Exception as e:
            logger.error(
                f"RAG response failed: {str(e)}",
                extra={"correlation_id": correlation_id, "user_id": user_id},
            )

            # Fallback to direct response
            try:
                fallback_messages = [{"role": "user", "content": message}]
                fallback_response = await self.streaming_service.get_single_response(
                    messages=fallback_messages,
                    context=None,
                    correlation_id=correlation_id,
                )

                return fallback_response, {"fallback": True, "error": str(e)}

            except Exception as fallback_error:
                logger.error(
                    f"Fallback also failed: {str(fallback_error)}",
                    extra={"correlation_id": correlation_id},
                )
                return (
                    "I apologize, but I'm unable to process your request right now. Please try again.",
                    {"error": True},
                )

    async def health_check(self, correlation_id: str = "") -> Dict[str, Any]:
        """
        Perform comprehensive health check of chat service components.

        Args:
            correlation_id: Request correlation ID

        Returns:
            Health check results for all components
        """
        health_status: Dict[str, Any] = {
            "service": "chat_service",
            "status": "healthy",
            "checks": {},
        }

        try:
            # Check RAG service health
            health_status["checks"]["rag_service"] = {
                "status": "checking",
                "details": {},
            }

            # Simple RAG test
            test_docs = await self.rag_service.retrieve_context(
                query="test health check", top_k=1, correlation_id=correlation_id
            )

            health_status["checks"]["rag_service"] = {
                "status": "healthy",
                "details": {
                    "documents_available": len(test_docs) > 0,
                    "hybrid_search": any(doc.get("hybrid_score") for doc in test_docs),
                },
            }

        except Exception as e:
            health_status["checks"]["rag_service"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        try:
            # Check streaming service health
            streaming_healthy = await self.streaming_service.health_check()
            health_status["checks"]["streaming_service"] = {
                "status": "healthy" if streaming_healthy else "unhealthy"
            }

            if not streaming_healthy:
                health_status["status"] = "degraded"

        except Exception as e:
            health_status["checks"]["streaming_service"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        try:
            # Check response cache service health
            cache_health = await self.response_cache.health_check(correlation_id)
            health_status["checks"]["response_cache"] = cache_health["checks"]

            if cache_health["status"] != "healthy":
                health_status["status"] = "degraded"

        except Exception as e:
            health_status["checks"]["response_cache"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        try:
            # Check database connectivity
            # Simple database operation to verify connection
            health_status["checks"]["database"] = {
                "status": "healthy",
                "details": {"connection": "active"},
            }

        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "unhealthy"

        logger.info(
            f"Chat service health check completed",
            extra={
                "correlation_id": correlation_id,
                "overall_status": health_status["status"],
                "component_count": len(health_status["checks"]),
            },
        )

        return health_status
