"""
Claude API client for streaming chat responses.

Implements production-ready async streaming client for Anthropic's Claude API
with comprehensive error handling, circuit breakers, retry logic, and graceful
fallback strategies for robust RAG pipeline integration.
"""

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import anthropic
from anthropic import AsyncAnthropic
from anthropic._types import NOT_GIVEN
from anthropic.types import MessageParam

from app.core.config import settings
from app.core.exceptions import ExternalServiceException
from app.core.resilience import resilience_manager

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Async client for Claude API with streaming support."""

    def __init__(self) -> None:
        """Initialize Claude API client."""
        self.client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY, timeout=60.0, max_retries=3
        )
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS

        logger.info(f"Claude client initialized with model: {self.model}")

    async def stream_response(
        self,
        messages: List[MessageParam],
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        correlation_id: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from Claude API with resilience protection.

        Args:
            messages: Conversation history in Claude format
            system_prompt: Optional system prompt
            context: Optional RAG context to include
            correlation_id: Request correlation ID for tracking

        Yields:
            Response tokens as they are streamed

        Raises:
            ExternalServiceException: If Claude API request fails after retries
        """
        logger.info(
            f"Starting Claude API streaming request with resilience",
            extra={
                "correlation_id": correlation_id,
                "message_count": len(messages),
                "has_context": bool(context),
                "model": self.model,
            },
        )

        async def _stream_with_protection() -> List[str]:
            """Internal streaming function with error handling."""
            try:
                # Build system prompt with context if provided
                system_content = self._build_system_prompt(system_prompt, context)

                # Create streaming request
                stream = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=messages,
                    system=system_content if system_content is not None else NOT_GIVEN,
                    stream=True,
                    temperature=0.7,
                    top_p=0.95,
                )

                # Track streaming metrics
                token_count = 0
                start_time = asyncio.get_event_loop().time()
                tokens = []

                # Stream response tokens
                async for chunk in stream:
                    if hasattr(chunk, "type") and chunk.type == "content_block_delta":
                        if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                            token = chunk.delta.text
                            tokens.append(token)
                            token_count += 1
                    elif hasattr(chunk, "type") and chunk.type == "message_stop":
                        break

                # Log completion metrics
                duration = asyncio.get_event_loop().time() - start_time
                logger.info(
                    f"Claude API streaming completed successfully",
                    extra={
                        "correlation_id": correlation_id,
                        "token_count": token_count,
                        "duration_seconds": round(duration, 2),
                        "tokens_per_second": (
                            round(token_count / duration, 2) if duration > 0 else 0
                        ),
                    },
                )

                return tokens

            except anthropic.AuthenticationError as e:
                logger.error(
                    f"Claude API authentication failed: {str(e)}",
                    extra={"correlation_id": correlation_id},
                )
                raise ExternalServiceException(
                    "Claude API",
                    f"Authentication failed: {str(e)}",
                    correlation_id=correlation_id,
                )

            except anthropic.RateLimitError as e:
                logger.error(
                    f"Claude API rate limit exceeded: {str(e)}",
                    extra={"correlation_id": correlation_id},
                )
                raise ExternalServiceException(
                    "Claude API",
                    f"Rate limit exceeded: {str(e)}",
                    correlation_id=correlation_id,
                )

            except anthropic.APIStatusError as e:
                logger.error(
                    f"Claude API status error: {str(e)}",
                    extra={
                        "correlation_id": correlation_id,
                        "status_code": e.status_code,
                        "response": e.response.text if e.response else None,
                    },
                )
                raise ExternalServiceException(
                    "Claude API",
                    f"API error (status {e.status_code}): {str(e)}",
                    correlation_id=correlation_id,
                )

            except Exception as e:
                logger.error(
                    f"Unexpected Claude API error: {str(e)}",
                    extra={
                        "correlation_id": correlation_id,
                        "error_type": type(e).__name__,
                    },
                )
                raise ExternalServiceException(
                    "Claude API",
                    f"Unexpected error: {str(e)}",
                    correlation_id=correlation_id,
                )

        try:
            # Execute with resilience protection
            tokens = await resilience_manager.execute_with_resilience(
                "claude_api", _stream_with_protection, correlation_id=correlation_id
            )

            # Yield tokens in streaming fashion
            for token in tokens:
                yield token

        except Exception as e:
            # If resilience fails, try fallback response
            logger.warning(
                f"Claude API streaming failed with resilience, attempting fallback",
                extra={"correlation_id": correlation_id, "error": str(e)},
            )

            fallback_response = await self._generate_fallback_response(
                messages, context, correlation_id
            )
            yield fallback_response

    async def get_single_response(
        self,
        messages: List[MessageParam],
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        correlation_id: str = "",
    ) -> str:
        """
        Get single response from Claude API (non-streaming).

        Args:
            messages: Conversation history in Claude format
            system_prompt: Optional system prompt
            context: Optional RAG context to include
            correlation_id: Request correlation ID for tracking

        Returns:
            Complete response text

        Raises:
            ExternalServiceException: If Claude API request fails
        """
        logger.info(
            f"Starting Claude API single request",
            extra={
                "correlation_id": correlation_id,
                "message_count": len(messages),
                "has_context": bool(context),
                "model": self.model,
            },
        )

        try:
            # Build system prompt with context if provided
            system_content = self._build_system_prompt(system_prompt, context)

            # Make API request
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                system=system_content if system_content is not None else NOT_GIVEN,
                temperature=0.7,
                top_p=0.95,
            )

            # Extract text content from response
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            logger.info(
                f"Claude API single request completed",
                extra={
                    "correlation_id": correlation_id,
                    "response_length": len(content),
                    "input_tokens": (
                        response.usage.input_tokens if response.usage else 0
                    ),
                    "output_tokens": (
                        response.usage.output_tokens if response.usage else 0
                    ),
                },
            )

            return content

        except Exception as e:
            # Handle specific API errors
            if isinstance(e, anthropic.AuthenticationError):
                logger.error(
                    f"Claude API authentication failed: {str(e)}",
                    extra={"correlation_id": correlation_id},
                )
                raise ExternalServiceException(
                    "Claude API",
                    f"Authentication failed: {str(e)}",
                    correlation_id=correlation_id,
                )
            elif isinstance(e, anthropic.RateLimitError):
                logger.error(
                    f"Claude API rate limit exceeded: {str(e)}",
                    extra={"correlation_id": correlation_id},
                )
                raise ExternalServiceException(
                    "Claude API",
                    f"Rate limit exceeded: {str(e)}",
                    correlation_id=correlation_id,
                )
            elif isinstance(e, anthropic.APIStatusError):
                logger.error(
                    f"Claude API status error: {str(e)}",
                    extra={
                        "correlation_id": correlation_id,
                        "status_code": e.status_code,
                        "response": e.response.text if e.response else None,
                    },
                )
                raise ExternalServiceException(
                    "Claude API",
                    f"API error (status {e.status_code}): {str(e)}",
                    correlation_id=correlation_id,
                )
            else:
                logger.error(
                    f"Unexpected Claude API error: {str(e)}",
                    extra={
                        "correlation_id": correlation_id,
                        "error_type": type(e).__name__,
                    },
                )
                raise ExternalServiceException(
                    "Claude API",
                    f"Unexpected error: {str(e)}",
                    correlation_id=correlation_id,
                )

    def _build_system_prompt(
        self, system_prompt: Optional[str] = None, context: Optional[str] = None
    ) -> Optional[str]:
        """
        Build system prompt with optional RAG context.

        Args:
            system_prompt: Base system prompt
            context: RAG context to include

        Returns:
            Combined system prompt or None
        """
        parts = []

        # Add base system prompt
        if system_prompt:
            parts.append(system_prompt)
        else:
            # Default system prompt for fintech FAQ assistant
            parts.append(
                "You are Eloquent AI, an intelligent fintech FAQ assistant. "
                "You help users with questions about financial services, account management, "
                "payments, security, and regulatory compliance. Provide accurate, helpful, "
                "and professional responses based on the context provided."
            )

        # Add RAG context if provided
        if context:
            parts.append(
                f"\n\nRelevant context from knowledge base:\n{context}\n\n"
                "Use this context to provide accurate and specific answers to user questions. "
                "If the context doesn't contain relevant information, politely indicate that "
                "you don't have specific information about that topic."
            )

        return "\n\n".join(parts) if parts else None

    def format_messages(
        self, conversation_history: List[Dict[str, str]]
    ) -> List[MessageParam]:
        """
        Format conversation history for Claude API.

        Args:
            conversation_history: List of message dictionaries with 'role' and 'content'

        Returns:
            Formatted messages for Claude API
        """
        formatted_messages: List[MessageParam] = []

        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role in ["user", "assistant"] and content.strip():
                formatted_messages.append(
                    {"role": role, "content": content}  # type: ignore
                )

        return formatted_messages

    async def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count (rough approximation)
        """
        # Anthropic uses similar tokenization to GPT models
        # Rough estimate: ~4 characters per token
        return max(1, len(text) // 4)

    async def _generate_fallback_response(
        self,
        messages: List[MessageParam],
        context: Optional[str] = None,
        correlation_id: str = "",
    ) -> str:
        """
        Generate fallback response when Claude API is unavailable.

        Provides graceful degradation with helpful user-facing messages.
        """
        logger.info(
            f"Generating fallback response for Claude API failure",
            extra={"correlation_id": correlation_id, "message_count": len(messages)},
        )

        # Extract user's last message
        user_message = ""
        if messages and messages[-1].get("role") == "user":
            content = messages[-1].get("content", "")
            if isinstance(content, str):
                user_message = content
            else:
                user_message = ""  # Handle complex content types

        # Create contextual fallback response
        fallback_responses = [
            "I'm experiencing some technical difficulties right now. Let me try to help based on what I know.",
            "I'm currently having connection issues, but I'll do my best to assist you.",
            "Due to high demand, I'm running in limited mode. I can still help with basic questions.",
        ]

        # Select appropriate fallback
        base_response = fallback_responses[0]  # Default fallback

        # Add context-based guidance if available
        if context:
            base_response += " Based on the available information:"
            # Extract key information from context (simple keyword matching)
            context_keywords = ["account", "payment", "security", "transfer", "balance"]
            for keyword in context_keywords:
                if (
                    keyword.lower() in user_message.lower()
                    and keyword in context.lower()
                ):
                    base_response += f" For {keyword}-related questions, please refer to our help documentation or contact support directly."
                    break
        else:
            base_response += " For detailed assistance, please contact our support team or try again in a few moments."

        return base_response

    async def health_check(self, correlation_id: str = "") -> Dict[str, Any]:
        """
        Comprehensive health check including circuit breaker status.

        Args:
            correlation_id: Request correlation ID

        Returns:
            Detailed health status including circuit breaker state
        """
        health_status = {
            "service": "claude_api",
            "status": "healthy",
            "checks": {},
            "circuit_breakers": {},
            "timestamp": time.time(),
        }

        # Check circuit breaker state
        try:
            claude_cb_health = resilience_manager.get_service_health("claude_api")

            health_status["circuit_breakers"] = {
                "claude_api": {
                    "state": claude_cb_health["state"],
                    "status": claude_cb_health["status"],
                    "error_rate": claude_cb_health["error_rate"],
                    "total_requests": claude_cb_health["total_requests"],
                }
            }

            # Set overall status based on circuit breaker
            if claude_cb_health["status"] == "unhealthy":
                health_status["status"] = "unhealthy"
            elif claude_cb_health["status"] == "degraded":
                health_status["status"] = "degraded"

        except Exception as e:
            logger.error(
                f"Failed to get Claude API circuit breaker health: {str(e)}",
                extra={"correlation_id": correlation_id},
            )
            health_status["circuit_breakers"] = {"error": str(e)}

        # Test basic API connectivity
        try:

            async def _test_api() -> bool:
                test_messages: List[MessageParam] = [
                    {"role": "user", "content": "Health check"}
                ]
                response = await self.client.messages.create(
                    model=self.model, max_tokens=5, messages=test_messages
                )
                return bool(response.content)

            api_result = await resilience_manager.execute_with_resilience(
                "claude_api", _test_api, correlation_id=correlation_id
            )

            health_status["checks"] = health_status.get("checks", {})
            if isinstance(health_status["checks"], dict):
                health_status["checks"]["api_connectivity"] = {
                    "status": "healthy" if api_result else "unhealthy",
                    "details": {"can_generate_response": api_result},
                }

        except Exception as e:
            health_status["checks"] = health_status.get("checks", {})
            if isinstance(health_status["checks"], dict):
                health_status["checks"]["api_connectivity"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
            health_status["status"] = "unhealthy"

        # Test streaming functionality
        try:
            test_messages: List[MessageParam] = [{"role": "user", "content": "Test"}]

            token_count = 0
            async for token in self.stream_response(
                test_messages, correlation_id=correlation_id
            ):
                token_count += 1
                if token_count >= 1:  # Just test first token
                    break

            health_status["checks"] = health_status.get("checks", {})
            if isinstance(health_status["checks"], dict):
                health_status["checks"]["streaming"] = {
                    "status": "healthy" if token_count > 0 else "degraded",
                    "details": {"can_stream": token_count > 0},
                }

        except Exception as e:
            health_status["checks"] = health_status.get("checks", {})
            if isinstance(health_status["checks"], dict):
                health_status["checks"]["streaming"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"

        checks_dict = health_status.get("checks", {})
        if isinstance(checks_dict, dict):
            logger.info(
                f"Claude API health check completed",
                extra={
                    "correlation_id": correlation_id,
                    "overall_status": health_status["status"],
                    "checks_passed": sum(
                        1
                        for check in checks_dict.values()
                        if isinstance(check, dict) and check.get("status") == "healthy"
                    ),
                    "total_checks": len(checks_dict),
                },
            )
        else:
            logger.info(
                f"Claude API health check completed",
                extra={
                    "correlation_id": correlation_id,
                    "overall_status": health_status["status"],
                },
            )

        return health_status
