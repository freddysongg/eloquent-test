"""
Streaming response service for real-time AI responses via Claude API.

Implements async streaming client for Claude API with WebSocket
communication support and proper error handling.
"""

import logging
import re
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
        Stream AI response using Claude API with markdown optimization.

        Args:
            messages: Conversation history with role and content
            context: Optional RAG context information
            system_prompt: Optional custom system prompt
            correlation_id: Request correlation ID

        Yields:
            Response tokens optimized for markdown rendering
        """
        logger.info(
            f"Starting Claude API response stream with markdown optimization",
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

            # Enhanced system prompt for better markdown formatting
            enhanced_system_prompt = self._enhance_system_prompt_for_markdown(
                system_prompt
            )

            # Stream response from Claude API
            accumulated_content = ""

            async for token in self.claude_client.stream_response(
                messages=claude_messages,
                system_prompt=enhanced_system_prompt,
                context=context,
                correlation_id=correlation_id,
            ):
                # Accumulate content for context-aware formatting
                accumulated_content += token

                # Apply markdown-friendly formatting
                formatted_token = self._format_token_for_markdown(
                    token, accumulated_content
                )

                yield formatted_token

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

    def _enhance_system_prompt_for_markdown(
        self, system_prompt: Optional[str] = None
    ) -> str:
        """
        Enhance system prompt to encourage markdown-friendly formatting.

        Args:
            system_prompt: Original system prompt

        Returns:
            Enhanced system prompt with markdown guidance
        """
        base_prompt = system_prompt or self.build_system_prompt()

        markdown_enhancement = (
            "\n\nFormatting Guidelines:\n"
            "- Use proper markdown syntax for code blocks with language specification\n"
            "- Structure responses with clear headings (##, ###) when appropriate\n"
            "- Use bullet points (-) and numbered lists (1.) for better readability\n"
            "- Emphasize important terms with **bold** or *italic* text\n"
            "- Use > blockquotes for important notes or warnings\n"
            "- Format inline code with `backticks`\n"
            "- Ensure proper line breaks between sections\n"
            "- Use tables when presenting structured data"
        )

        return base_prompt + markdown_enhancement

    def _format_token_for_markdown(self, token: str, accumulated_content: str) -> str:
        """
        Format streaming token for optimal markdown rendering.

        Args:
            token: Current streaming token
            accumulated_content: All content streamed so far

        Returns:
            Formatted token optimized for markdown
        """
        # Don't modify individual characters or very short tokens
        if len(token) <= 1:
            return token

        # Check if we're in a code block context
        code_block_matches = re.findall(r"```", accumulated_content)
        in_code_block = len(code_block_matches) % 2 == 1

        # Check if we're in inline code context
        inline_code_matches = re.findall(r"(?<!`)`(?!`)", accumulated_content)
        in_inline_code = len(inline_code_matches) % 2 == 1

        # Skip formatting if we're inside code blocks
        if in_code_block or in_inline_code:
            return token

        formatted_token = token

        # Enhance list formatting - ensure proper spacing after list markers
        if re.match(r"^[\-\*\+]\s", token) or re.match(r"^\d+\.\s", token):
            # Already properly formatted list item
            pass
        elif token.startswith("-") and len(token) > 1 and token[1] != " ":
            # Add space after dash for list items
            formatted_token = "- " + token[1:]
        elif re.match(r"^\d+\.", token) and not re.match(r"^\d+\.\s", token):
            # Add space after numbered list marker
            formatted_token = re.sub(r"^(\d+\.)", r"\1 ", token)

        # Ensure proper spacing around emphasis markers
        if "**" in token and not in_code_block:
            # Ensure spaces around bold text if not at word boundaries
            formatted_token = re.sub(r"(?<!\s)\*\*(?=\w)", r" **", formatted_token)
            formatted_token = re.sub(r"(?<=\w)\*\*(?!\s)", r"** ", formatted_token)

        # Handle code block language hints
        if token.startswith("```") and len(token) > 3:
            # Extract potential language from the token
            possible_lang = token[3:].strip().lower()
            common_langs = [
                "python",
                "javascript",
                "json",
                "sql",
                "bash",
                "typescript",
                "html",
                "css",
            ]

            # If it looks like it might be a language, ensure proper formatting
            if any(lang in possible_lang for lang in common_langs):
                formatted_token = "```" + possible_lang + "\n"

        return formatted_token

    def validate_markdown_structure(self, content: str) -> Dict[str, Any]:
        """
        Validate markdown structure and provide formatting suggestions.

        Args:
            content: Full response content to validate

        Returns:
            Validation results with suggestions
        """
        issues = []
        suggestions = []

        # Check for unbalanced code blocks
        code_blocks = re.findall(r"```", content)
        if len(code_blocks) % 2 != 0:
            issues.append("unbalanced_code_blocks")
            suggestions.append("Ensure all code blocks are properly closed with ```")

        # Check for unbalanced inline code
        inline_code = re.findall(r"(?<!`)`(?!`)", content)
        if len(inline_code) % 2 != 0:
            issues.append("unbalanced_inline_code")
            suggestions.append("Ensure all inline code is properly closed with `")

        # Check for proper list formatting
        list_lines = re.findall(r"^[\-\*\+\d\.]\s*\S", content, re.MULTILINE)
        improper_lists = re.findall(
            r"^[\-\*\+](?!\s)|^\d+\.(?!\s)", content, re.MULTILINE
        )

        if improper_lists:
            issues.append("improper_list_formatting")
            suggestions.append("Add spaces after list markers (- or 1.)")

        # Check for heading structure
        headings = re.findall(r"^#{1,6}\s+.+$", content, re.MULTILINE)

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "stats": {
                "code_blocks": len(code_blocks) // 2,
                "inline_code_spans": len(inline_code) // 2,
                "list_items": len(list_lines),
                "headings": len(headings),
            },
        }
