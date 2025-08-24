"""
Claude API client for streaming chat responses.

Implements async streaming client for Anthropic's Claude API with proper
error handling, rate limiting, and context management.
"""

import asyncio
import logging
from typing import AsyncGenerator, Dict, List, Optional

import anthropic
from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam

from app.core.config import settings
from app.core.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Async client for Claude API with streaming support."""
    
    def __init__(self) -> None:
        """Initialize Claude API client."""
        self.client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=60.0,
            max_retries=3
        )
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS
        
        logger.info(f"Claude client initialized with model: {self.model}")
    
    async def stream_response(
        self,
        messages: List[MessageParam],
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        correlation_id: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from Claude API.
        
        Args:
            messages: Conversation history in Claude format
            system_prompt: Optional system prompt
            context: Optional RAG context to include
            correlation_id: Request correlation ID for tracking
        
        Yields:
            Response tokens as they are streamed
        
        Raises:
            ExternalServiceException: If Claude API request fails
        """
        logger.info(
            f"Starting Claude API streaming request",
            extra={
                "correlation_id": correlation_id,
                "message_count": len(messages),
                "has_context": bool(context),
                "model": self.model
            }
        )
        
        try:
            # Build system prompt with context if provided
            system_content = self._build_system_prompt(system_prompt, context)
            
            # Create streaming request
            stream = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                system=system_content if system_content else None,
                stream=True,
                temperature=0.7,
                top_p=0.95
            )
            
            # Track streaming metrics
            token_count = 0
            start_time = asyncio.get_event_loop().time()
            
            # Stream response tokens
            async for chunk in stream:
                if chunk.type == "content_block_delta":
                    if hasattr(chunk.delta, 'text'):
                        token = chunk.delta.text
                        yield token
                        token_count += 1
                elif chunk.type == "message_stop":
                    break
            
            # Log completion metrics
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(
                f"Claude API streaming completed",
                extra={
                    "correlation_id": correlation_id,
                    "token_count": token_count,
                    "duration_seconds": round(duration, 2),
                    "tokens_per_second": round(token_count / duration, 2) if duration > 0 else 0
                }
            )
            
        except anthropic.AuthenticationError as e:
            logger.error(
                f"Claude API authentication failed: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Claude API",
                f"Authentication failed: {str(e)}",
                correlation_id=correlation_id
            )
            
        except anthropic.RateLimitError as e:
            logger.error(
                f"Claude API rate limit exceeded: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Claude API",
                f"Rate limit exceeded: {str(e)}",
                correlation_id=correlation_id
            )
            
        except anthropic.APIStatusError as e:
            logger.error(
                f"Claude API status error: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "status_code": e.status_code,
                    "response": e.response.text if e.response else None
                }
            )
            raise ExternalServiceException(
                "Claude API",
                f"API error (status {e.status_code}): {str(e)}",
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(
                f"Unexpected Claude API error: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            raise ExternalServiceException(
                "Claude API",
                f"Unexpected error: {str(e)}",
                correlation_id=correlation_id
            )
    
    async def get_single_response(
        self,
        messages: List[MessageParam],
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        correlation_id: str = ""
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
                "model": self.model
            }
        )
        
        try:
            # Build system prompt with context if provided
            system_content = self._build_system_prompt(system_prompt, context)
            
            # Make API request
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                system=system_content if system_content else None,
                temperature=0.7,
                top_p=0.95
            )
            
            # Extract text content from response
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text
            
            logger.info(
                f"Claude API single request completed",
                extra={
                    "correlation_id": correlation_id,
                    "response_length": len(content),
                    "input_tokens": response.usage.input_tokens if response.usage else 0,
                    "output_tokens": response.usage.output_tokens if response.usage else 0
                }
            )
            
            return content
            
        except Exception as e:
            # Reuse error handling from stream_response
            if isinstance(e, (anthropic.AuthenticationError, anthropic.RateLimitError, anthropic.APIStatusError)):
                # Re-raise to be handled by stream_response error handling
                async for _ in self.stream_response(messages, system_prompt, context, correlation_id):
                    pass  # This will trigger the error handling
            else:
                raise ExternalServiceException(
                    "Claude API",
                    f"Unexpected error: {str(e)}",
                    correlation_id=correlation_id
                )
    
    def _build_system_prompt(
        self,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
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
        self,
        conversation_history: List[Dict[str, str]]
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
                formatted_messages.append({
                    "role": role,  # type: ignore
                    "content": content
                })
        
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
    
    async def health_check(self) -> bool:
        """
        Check Claude API health.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            test_messages: List[MessageParam] = [
                {"role": "user", "content": "Hello"}
            ]
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=test_messages
            )
            
            return bool(response.content)
            
        except Exception as e:
            logger.error(f"Claude API health check failed: {str(e)}")
            return False