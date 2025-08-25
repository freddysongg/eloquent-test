"""
Streaming response service for real-time AI responses via Claude API.

Implements async streaming client for Claude API with WebSocket
communication support and proper error handling.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.integrations.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class StreamingService:
    """Service for streaming AI responses via Claude API and WebSockets."""

    def __init__(self) -> None:
        """Initialize streaming service with Claude API client."""
        self.claude_client = ClaudeClient()
        logger.info("Streaming service initialized with Claude client")

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        correlation_id: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response using Claude API.

        Args:
            messages: Conversation history with role and content
            context: Optional RAG context information
            system_prompt: Optional custom system prompt
            correlation_id: Request correlation ID

        Yields:
            Response tokens as they are generated
        """
        logger.info(
            f"Starting Claude API response stream",
            extra={
                "correlation_id": correlation_id,
                "message_count": len(messages),
                "has_context": bool(context),
                "has_system_prompt": bool(system_prompt),
            },
        )

        try:
            # Convert messages to Claude API format
            claude_messages = self.claude_client.format_messages(messages)

            # Stream response from Claude API
            async for token in self.claude_client.stream_response(
                messages=claude_messages,
                system_prompt=system_prompt,
                context=context,
                correlation_id=correlation_id,
            ):
                yield token

        except Exception as e:
            logger.error(
                f"Streaming response failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            # Yield error message to client
            yield f"\n\n[Error: Unable to generate response. Please try again.]"

    async def get_single_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        correlation_id: str = "",
    ) -> str:
        """
        Get complete AI response (non-streaming).

        Args:
            messages: Conversation history with role and content
            context: Optional RAG context information
            system_prompt: Optional custom system prompt
            correlation_id: Request correlation ID

        Returns:
            Complete response text
        """
        logger.info(
            f"Getting single Claude API response",
            extra={
                "correlation_id": correlation_id,
                "message_count": len(messages),
                "has_context": bool(context),
            },
        )

        try:
            # Convert messages to Claude API format
            claude_messages = self.claude_client.format_messages(messages)

            # Get complete response from Claude API
            response = await self.claude_client.get_single_response(
                messages=claude_messages,
                system_prompt=system_prompt,
                context=context,
                correlation_id=correlation_id,
            )

            return response

        except Exception as e:
            logger.error(
                f"Single response failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            return "I apologize, but I'm unable to generate a response right now. Please try again."

    async def stream_with_context(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        retrieved_documents: List[Dict[str, Any]],
        correlation_id: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        Stream response with RAG context integration.

        Args:
            user_message: Current user message
            conversation_history: Previous conversation messages
            retrieved_documents: Documents from RAG pipeline
            correlation_id: Request correlation ID

        Yields:
            Response tokens with context-aware generation
        """
        logger.info(
            f"Streaming response with RAG context",
            extra={
                "correlation_id": correlation_id,
                "message_length": len(user_message),
                "history_count": len(conversation_history),
                "context_docs": len(retrieved_documents),
            },
        )

        try:
            # Build context from retrieved documents
            context_parts = []
            for i, doc in enumerate(retrieved_documents[:5]):  # Limit to top 5
                content_raw = doc.get("content", "")
                content = content_raw.strip() if isinstance(content_raw, str) else ""
                category_raw = doc.get("category", "")
                category = category_raw if isinstance(category_raw, str) else ""

                if content:
                    doc_header = f"[Context {i+1}"
                    if category:
                        doc_header += f" - {category.title()}"
                    doc_header += "]"

                    context_parts.append(f"{doc_header}\n{content}")

            context = "\n\n".join(context_parts) if context_parts else None

            # Build complete conversation
            messages = conversation_history + [
                {"role": "user", "content": user_message}
            ]

            # Stream response with context
            async for token in self.stream_response(
                messages=messages, context=context, correlation_id=correlation_id
            ):
                yield token

        except Exception as e:
            logger.error(
                f"Context streaming failed: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            yield f"\n\n[Error: Unable to process your request with context. Please try again.]"

    async def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text using Claude client.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        return await self.claude_client.estimate_tokens(text)

    async def health_check(self) -> bool:
        """
        Check streaming service health.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            health_result = await self.claude_client.health_check()
            return (
                isinstance(health_result, dict)
                and health_result.get("status") == "healthy"
            )

        except Exception as e:
            logger.error(f"Streaming service health check failed: {str(e)}")
            return False

    def build_system_prompt(self, user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Build system prompt for fintech FAQ assistant.

        Args:
            user_context: Optional user context information

        Returns:
            Formatted system prompt
        """
        base_prompt = (
            "You are Eloquent AI, an intelligent and helpful fintech FAQ assistant. "
            "You specialize in providing accurate, professional, and clear answers about "
            "financial services, account management, payments, transactions, security, "
            "fraud prevention, and regulatory compliance.\n\n"
            "Guidelines:\n"
            "- Provide specific, actionable answers based on the context provided\n"
            "- If you don't have specific information, clearly state this and suggest alternatives\n"
            "- Always prioritize accuracy and compliance with financial regulations\n"
            "- Use clear, professional language appropriate for customers\n"
            "- For security-related questions, emphasize safety and best practices\n"
            "- For account or transaction issues, guide users to appropriate support channels\n"
        )

        if user_context:
            user_info: List[str] = []
            if user_context.get("is_authenticated"):
                user_info.append(
                    "The user is authenticated and logged into their account."
                )
            if user_context.get("account_type"):
                user_info.append(f"Account type: {user_context['account_type']}")

            if user_info:
                base_prompt += f"\n\nUser Context:\n" + "\n".join(user_info)

        return base_prompt
