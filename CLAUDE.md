# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 1. Project Overview

**Eloquent AI** - Production-ready AI-powered chatbot using retrieval-augmented generation (RAG) for fintech FAQ support.

- **Vision:** Reduce AI hallucinations through RAG-enhanced responses using Pinecone vector database and Claude API
- **Current Phase:** Architecture planning and foundation setup (Phase 1 of 5-phase roadmap)
- **Key Architecture:** Next.js 14 frontend + FastAPI backend + RAG pipeline with Pinecone + Claude API streaming
- **Development Strategy:** Modular monolith approach with clear service boundaries, production-ready from day one

## 2. Project Structure

**⚠️ CRITICAL: AI agents MUST read the [Project Structure documentation](/docs/ai-context/project-structure.md) before attempting any task to understand the complete technology stack, file tree and project organization.**

Eloquent AI follows a **microservices with modular monolith approach** - single backend service with clear module boundaries for easier deployment while maintaining separation of concerns. For the complete tech stack and file tree structure, see [docs/ai-context/project-structure.md](/docs/ai-context/project-structure.md).

### High-Level Architecture

**Frontend (Next.js 14 + Vercel)**
- TypeScript 5.x with App Router
- Real-time chat interface with WebSocket streaming
- Tailwind CSS + Shadcn/ui components
- Zustand (client state) + React Query (server state)

**Backend (FastAPI + AWS App Runner)**
- Python 3.11+ with SQLAlchemy 2.0 async
- RAG pipeline with hybrid search (Pinecone + BM25)
- WebSocket server for real-time streaming
- Multi-tier rate limiting with Redis

**AI & Data Layer**
- **Pinecone Vector DB**: Pre-configured with fintech FAQ data (17 records, cosine similarity, 1024 dims)
- **Claude API**: Streaming responses with context injection
- **PostgreSQL (Primary)**: Chat history, user management with RLS via SQLAlchemy 2.0 async
- **DynamoDB (Optional)**: Sessions, rate limits, analytics, cache tables for enhanced performance
- **Redis (ElastiCache)**: Caching, rate limiting, pub/sub messaging

**Authentication & Security**
- Clerk Auth with JWT token management
- Anonymous user support with cookie-based sessions
- Row Level Security (RLS) for data isolation

## 3. Coding Standards & AI Instructions

### General Instructions
- Your most important job is to manage your own context. Always read any relevant files BEFORE planning changes.
- When updating documentation, keep updates concise and on point to prevent bloat.
- Write code following KISS, YAGNI, and DRY principles.
- When in doubt follow proven best practices for implementation.
- Do not commit to git without user approval.
- Do not run any servers, rather tell the user to run servers for testing.
- Always consider industry standard libraries/frameworks first over custom implementations.
- Never mock anything. Never use placeholders. Never omit code.
- Apply SOLID principles where relevant. Use modern framework features rather than reinventing solutions.
- Be brutally honest about whether an idea is good or bad.
- Make side effects explicit and minimal.
- Design database schema to be evolution-friendly (avoid breaking changes).


### File Organization & Modularity
- Default to creating multiple small, focused files rather than large monolithic ones
- Each file should have a single responsibility and clear purpose
- Keep files under 350 lines when possible - split larger files by extracting utilities, constants, types, or logical components into separate modules
- Separate concerns: utilities, constants, types, components, and business logic into different files
- Prefer composition over inheritance - use inheritance only for true 'is-a' relationships, favor composition for 'has-a' or behavior mixing

- Follow existing project structure and conventions - place files in appropriate directories. Create new directories and move files if deemed appropriate.
- Use well defined sub-directories to keep things organized and scalable
- Structure projects with clear folder hierarchies and consistent naming conventions
- Import/export properly - design for reusability and maintainability

### Type Hints (REQUIRED)
- **Always** use type hints for function parameters and return values
- Use `from typing import` for complex types
- Prefer `Optional[T]` over `Union[T, None]`
- Use Pydantic models for data structures

```python
# Good - RAG Pipeline Example
from typing import Optional, List, Dict, Tuple
from pydantic import BaseModel

async def process_rag_query(
    query: str,
    chat_id: str,
    context_limit: Optional[int] = 5
) -> Tuple[str, Dict[str, Any]]:
    """Process RAG query with context retrieval."""
    pass

class ChatRequestSchema(BaseModel):
    message: str
    chat_id: Optional[str] = None
    stream: bool = True
```

### Naming Conventions
- **Classes**: PascalCase (e.g., `RAGPipeline`, `ChatService`)
- **Functions/Methods**: snake_case (e.g., `process_message`, `retrieve_context`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_CONTEXT_LENGTH`, `PINECONE_INDEX`)
- **Private methods**: Leading underscore (e.g., `_validate_query`, `_build_context`)
- **Pydantic Models**: PascalCase with `Schema` suffix (e.g., `ChatRequestSchema`, `MessageSchema`)


### Documentation Requirements
- Every module needs a docstring
- Every public function needs a docstring
- Use Google-style docstrings
- Include type information in docstrings

```python
async def retrieve_context(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant context from Pinecone vector database.

    Args:
        query: User query for context retrieval
        top_k: Number of relevant documents to retrieve

    Returns:
        List of context documents with relevance scores

    Raises:
        PineconeError: If vector database query fails
        ValueError: If query is empty or top_k is invalid
    """
    pass
```

### Security First
- Never trust external inputs - validate everything at the boundaries
- Keep secrets in environment variables, never in code
- Log security events (login attempts, auth failures, rate limits, permission denials) but never log sensitive data (conversation content, tokens, personal info)
- Authenticate users at the API gateway level - never trust client-side tokens
- Use Row Level Security (RLS) to enforce data isolation between users
- Design auth to work across all client types consistently
- Use secure authentication patterns for your platform
- Validate all authentication tokens server-side before creating sessions
- Sanitize all user inputs before storing or processing

### Error Handling
- Use specific exceptions over generic ones
- Always log errors with context
- Provide helpful error messages
- Fail securely - errors shouldn't reveal system internals

### Observable Systems & Logging Standards
- Every request needs a correlation ID for debugging
- Structure logs for machines, not humans - use JSON format with consistent fields (timestamp, level, correlation_id, event, context) for automated analysis
- Make debugging possible across service boundaries

### State Management
- Have one source of truth for each piece of state
- Make state changes explicit and traceable
- Design for stateless RAG processing - use session IDs for chat coordination, avoid storing conversation data in server memory
- Keep conversation history lightweight (text only) in PostgreSQL

### API Design Principles
- RESTful design with consistent URL patterns
- Use HTTP status codes correctly
- Version APIs from day one (/v1/, /v2/)
- Support pagination for list endpoints
- Use consistent JSON response format:
  - Success: `{ "data": {...}, "error": null }`
  - Error: `{ "data": null, "error": {"message": "...", "code": "..."} }`


## 4. Multi-Agent Workflows & Context Injection

### Automatic Context Injection for Sub-Agents
When using the Task tool to spawn sub-agents, the core project context (CLAUDE.md, project-structure.md, docs-overview.md) is automatically injected into their prompts via the subagent-context-injector hook. This ensures all sub-agents have immediate access to essential project documentation without the need of manual specification in each Task prompt.


## 5. MCP Server Integrations

### Gemini Consultation Server
**When to use:**
- Complex coding problems requiring deep analysis or multiple approaches
- Code reviews and architecture discussions
- Debugging complex issues across multiple files
- Performance optimization and refactoring guidance
- Detailed explanations of complex implementations
- Highly security relevant tasks

**Automatic Context Injection:**
- The kit's `gemini-context-injector.sh` hook automatically includes two key files for new sessions:
  - `/docs/ai-context/project-structure.md` - Complete project structure and tech stack
  - `/MCP-ASSISTANT-RULES.md` - Your project-specific coding standards and guidelines
- This ensures Gemini always has comprehensive understanding of your technology stack, architecture, and project standards

**Usage patterns:**
```python
# New consultation session (project structure auto-attached by hooks)
mcp__gemini__consult_gemini(
    specific_question="How should I optimize this voice pipeline?",
    problem_description="Need to reduce latency in real-time audio processing",
    code_context="Current pipeline processes audio sequentially...",
    attached_files=[
        "src/core/pipelines/voice_pipeline.py"  # Your specific files
    ],
    preferred_approach="optimize"
)

# Follow-up in existing session
mcp__gemini__consult_gemini(
    specific_question="What about memory usage?",
    session_id="session_123",
    additional_context="Implemented your suggestions, now seeing high memory usage"
)
```

**Key capabilities:**
- Persistent conversation sessions with context retention
- File attachment and caching for multi-file analysis
- Specialized assistance modes (solution, review, debug, optimize, explain)
- Session management for complex, multi-step problems

**Important:** Treat Gemini's responses as advisory feedback. Evaluate the suggestions critically, incorporate valuable insights into your solution, then proceed with your implementation.

### Context7 Documentation Server
**Repository**: [Context7 MCP Server](https://github.com/upstash/context7)

**When to use:**
- Working with external libraries/frameworks (React, FastAPI, Next.js, etc.)
- Need current documentation beyond training cutoff
- Implementing new integrations or features with third-party tools
- Troubleshooting library-specific issues

**Usage patterns:**
```python
# Resolve library name to Context7 ID
mcp__context7__resolve_library_id(libraryName="react")

# Fetch focused documentation
mcp__context7__get_library_docs(
    context7CompatibleLibraryID="/facebook/react",
    topic="hooks",
    tokens=8000
)
```

**Key capabilities:**
- Up-to-date library documentation access
- Topic-focused documentation retrieval
- Support for specific library versions
- Integration with current development practices



## 6. Development Commands & Architecture Patterns

### Key Architecture Patterns

#### RAG Pipeline Implementation
**Service Pattern**: RAG operations use a service layer pattern with clear separation:
- `RAGService`: Orchestrates retrieval and generation
- `PineconeRetriever`: Handles vector search queries  
- `ContextManager`: Manages context window optimization
- `StreamingService`: Handles real-time Claude API responses

```python
# Critical RAG Flow Pattern
async def process_message(query: str, chat_id: str) -> AsyncGenerator[str, None]:
    # 1. Retrieve context from Pinecone
    context = await retriever.retrieve(query, top_k=5)
    # 2. Build optimized context window
    prompt = context_manager.build_prompt(query, context, chat_history)
    # 3. Stream response from Claude API
    async for token in claude_client.stream(prompt):
        yield token
```

#### Repository Pattern for Data Access
All database operations use repository pattern for testability and abstraction:
- `ChatRepository`: Chat CRUD operations with RLS
- `MessageRepository`: Message storage with user isolation
- `UserRepository`: User management with Clerk integration

#### WebSocket Connection Management
Real-time features use connection manager pattern:
- `ConnectionManager`: Handles WebSocket lifecycle
- `MessageHandler`: Routes WebSocket events
- Redis pub/sub for multi-instance coordination

### Pre-configured External Services

#### Pinecone Vector Database
```python
# Pre-configured index settings (DO NOT CHANGE)
PINECONE_INDEX = "ai-powered-chatbot-challenge"
PINECONE_HOST = "https://ai-powered-chatbot-challenge-omkb0qa.svc.aped-4627-b74a.pinecone.io"
# Contains 17 fintech FAQ records, cosine similarity, 1024 dimensions
```

#### Rate Limiting Architecture
Multi-tier rate limiting implemented in middleware:
- Global: 1000 req/min per IP
- Authenticated: 100 req/min per user  
- Anonymous: 20 req/min per session
- LLM calls: 10 req/min per user

### Development Workflow

Since this is an architecture and planning project, there are no build commands yet. When implementation begins:

**Backend (FastAPI)**
- Development server: `uvicorn app.main:app --reload`
- Type checking: `mypy app/`
- Testing: `pytest`
- Linting: `black app/ && isort app/`

**Frontend (Next.js)**
- Development server: `npm run dev`
- Type checking: `npm run type-check`
- Testing: `npm test`
- Build: `npm run build`

**Database (PostgreSQL + DynamoDB)**
- Schema changes via migrations in `migrations/`
- Row Level Security policies defined per table

## 7. Post-Task Completion Protocol

### 1. Type Safety & Quality Checks
Run the appropriate commands based on what was modified:
- **Python projects**: Run mypy type checking  
- **TypeScript projects**: Run tsc --noEmit
- **Database changes**: Verify RLS policies and constraints

### 2. Integration Verification
- Test RAG pipeline end-to-end if modified
- Verify rate limiting if authentication touched
- Test WebSocket connections if real-time features changed
- Validate Pinecone queries if vector operations modified

### 3. Performance Validation
- API response times must be <200ms for non-LLM endpoints
- LLM streaming responses should start within 500ms
- Frontend load times must be <3s on 3G networks