# Eloquent AI - Project Structure & Technology Stack

This document provides the complete technology stack and file tree structure for the Eloquent AI chatbot project. **AI agents MUST read this file to understand the project organization before making any changes.**

## Project Overview

**Vision**: AI-powered chatbot with retrieval-augmented generation (RAG) for accurate, context-aware responses to fintech FAQ queries.

**Architecture**: Full-stack web application with Next.js frontend, FastAPI backend, and integrated AI/RAG pipeline using Pinecone vector database and Claude API.

**Business Context**: Fintech company FAQ bot covering Account & Registration, Payments & Transactions, Security & Fraud Prevention, Regulations & Compliance, and Technical Support.

## Complete Technology Stack

### Backend Technologies
- **Python 3.11+** - Core backend language
- **FastAPI 0.104+** - Web framework with type hints and async support
- **Uvicorn with Gunicorn** - ASGI server for production deployment
- **SQLAlchemy 2.0** - ORM with async support
- **Pydantic V2** - Data validation and settings management
- **Celery with Redis** - Task queue for background processing

### Frontend Technologies
- **Next.js 14** - React framework with App Router
- **TypeScript 5.x** - Type-safe JavaScript development
- **Tailwind CSS + Shadcn/ui** - Styling and component library
- **Zustand** - Client-side state management
- **React Query** - Server state management and caching
- **React Hook Form + Zod** - Form handling and validation
- **Socket.io-client** - Real-time WebSocket connections

### AI & Data Services
- **Claude API (Anthropic)** - Large language model for chat responses
- **Pinecone Vector Database** - Semantic search and RAG retrieval
  - Index: ai-powered-chatbot-challenge
  - Metric: cosine (1024 dimensions)
  - Model: llama-text-embed-v2
  - 17 pre-loaded fintech FAQ records
- **Custom RAG Pipeline** - Hybrid retrieval with semantic + keyword search
- **Custom Reranker** - Multi-stage document relevance optimization

### Database & Storage
- **Supabase (PostgreSQL)** - Primary database with real-time features
- **Redis (AWS ElastiCache)** - Caching, session management, and task queue
- **AWS S3** - Static asset storage

### Authentication & User Management
- **Clerk Auth** - User authentication and management
- **JWT Tokens** - Secure session management
- **Anonymous Session Tracking** - Cookie-based temporary user sessions

### Development & Quality Tools
- **Black** - Python code formatting
- **ESLint + Prettier** - JavaScript/TypeScript linting and formatting
- **MyPy** - Python static type checking
- **TypeScript Compiler** - Frontend type checking
- **pytest + pytest-asyncio** - Backend testing framework
- **Jest + React Testing Library** - Frontend unit testing
- **Playwright** - End-to-end testing
- **Factory Boy** - Test fixture generation
- **VCR.py** - HTTP request mocking for tests

### Infrastructure & DevOps
- **AWS App Runner** - Containerized backend hosting with auto-scaling
- **Vercel** - Frontend hosting with edge network
- **AWS API Gateway** - API management with rate limiting
- **Docker** - Containerization with multi-stage builds
- **GitHub Actions** - CI/CD pipeline automation
- **Terraform** - Infrastructure as code
- **AWS CloudWatch** - Application and infrastructure monitoring
- **Sentry** - Error tracking and performance monitoring

### Performance & Optimization
- **Redis Caching Strategy** - Multi-layer caching (application, chat history, RAG results)
- **CDN (CloudFront)** - Global content delivery
- **Connection Pooling** - Database and external service optimization
- **WebSocket Streaming** - Real-time response delivery
- **Code Splitting** - Frontend bundle optimization
- **Image Optimization** - Next.js automatic image processing

### Security & Compliance
- **TLS 1.3 Encryption** - Data in transit protection
- **JWT with Refresh Rotation** - Secure token management
- **Rate Limiting** - Multi-tier API protection
- **Input Validation** - Pydantic models and Zod schemas
- **Audit Logging** - Comprehensive security event tracking
- **CORS Configuration** - Cross-origin request security

## Complete Project Structure

```
eloquentai/
├── README.md                           # Project overview and setup
├── CLAUDE.md                           # Master AI context file
├── TECHNICAL.md                        # Complete technical specification
├── .gitignore                          # Git ignore patterns
├── docker-compose.yml                  # Local development environment
├── .vscode/                            # VS Code workspace configuration
│   ├── settings.json                   # IDE settings
│   ├── extensions.json                 # Recommended extensions
│   └── launch.json                     # Debug configurations
├── backend/                            # FastAPI Backend Application
│   ├── CONTEXT.md                      # Backend-specific AI context
│   ├── app/                            # Main application source
│   │   ├── main.py                     # FastAPI application entry point
│   │   ├── api/                        # API layer
│   │   │   ├── v1/                     # API version 1
│   │   │   │   ├── endpoints/          # API route definitions
│   │   │   │   │   ├── chat.py         # Chat endpoints
│   │   │   │   │   ├── auth.py         # Authentication endpoints
│   │   │   │   │   ├── users.py        # User management endpoints
│   │   │   │   │   └── webhooks.py     # Webhook endpoints (Clerk, etc.)
│   │   │   │   └── router.py           # Main API router
│   │   │   └── dependencies/           # Dependency injection
│   │   ├── core/                       # Core application logic
│   │   │   ├── config.py               # Application settings
│   │   │   ├── security.py             # Security utilities
│   │   │   └── exceptions.py           # Custom exception handlers
│   │   ├── models/                     # SQLAlchemy models
│   │   │   ├── chat.py                 # Chat data models
│   │   │   ├── user.py                 # User data models
│   │   │   └── message.py              # Message data models
│   │   ├── schemas/                    # Pydantic schemas
│   │   │   ├── chat.py                 # Chat request/response schemas
│   │   │   ├── user.py                 # User schemas
│   │   │   └── message.py              # Message schemas
│   │   ├── services/                   # Business logic services
│   │   │   ├── chat_service.py         # Chat orchestration
│   │   │   ├── rag_service.py          # RAG pipeline service
│   │   │   ├── streaming_service.py    # Response streaming
│   │   │   └── auth_service.py         # Authentication logic
│   │   ├── repositories/               # Data access layer
│   │   │   ├── chat_repository.py      # Chat data operations
│   │   │   └── user_repository.py      # User data operations
│   │   ├── rag/                        # RAG system components
│   │   │   ├── pipeline.py             # Main RAG pipeline
│   │   │   ├── retriever.py            # Document retrieval
│   │   │   ├── reranker.py             # Result reranking
│   │   │   └── context_manager.py      # Context window management
│   │   └── websocket/                  # WebSocket handling
│   │       ├── connection_manager.py   # Connection management
│   │       └── handlers.py             # WebSocket event handlers
│   ├── tests/                          # Backend test suite
│   │   ├── unit/                       # Unit tests
│   │   ├── integration/                # Integration tests
│   │   └── fixtures/                   # Test fixtures and data
│   ├── migrations/                     # Database migrations
│   ├── docker/                         # Docker configurations
│   ├── pyproject.toml                  # Poetry dependencies
│   └── .env.example                    # Environment variables template
├── frontend/                           # Next.js Frontend Application
│   ├── CONTEXT.md                      # Frontend-specific AI context
│   ├── app/                            # Next.js App Router
│   │   ├── (auth)/                     # Authentication routes
│   │   │   ├── login/                  # Login page
│   │   │   │   └── page.tsx
│   │   │   └── register/               # Registration page
│   │   │       └── page.tsx
│   │   ├── (chat)/                     # Chat application routes
│   │   │   ├── layout.tsx              # Chat layout
│   │   │   ├── page.tsx                # Main chat page
│   │   │   └── [chatId]/               # Individual chat view
│   │   │       └── page.tsx
│   │   ├── api/                        # Next.js API routes
│   │   │   └── chat/
│   │   │       └── stream/             # Client-side streaming
│   │   ├── globals.css                 # Global styles
│   │   └── layout.tsx                  # Root layout
│   ├── components/                     # React components
│   │   ├── chat/                       # Chat-specific components
│   │   │   ├── ChatInterface.tsx       # Main chat interface
│   │   │   ├── MessageList.tsx         # Message display list
│   │   │   ├── MessageInput.tsx        # Message input form
│   │   │   ├── StreamingMessage.tsx    # Real-time message streaming
│   │   │   └── ChatSidebar.tsx         # Chat navigation sidebar
│   │   ├── ui/                         # Shadcn/ui components
│   │   └── providers/                  # React context providers
│   │       ├── AuthProvider.tsx        # Authentication context
│   │       ├── SocketProvider.tsx      # WebSocket context
│   │       └── QueryProvider.tsx       # React Query setup
│   ├── hooks/                          # Custom React hooks
│   │   ├── useChat.ts                  # Chat management hook
│   │   ├── useSocket.ts                # WebSocket connection hook
│   │   └── useAuth.ts                  # Authentication hook
│   ├── lib/                            # Utility libraries
│   │   ├── api/                        # API client setup
│   │   ├── socket/                     # WebSocket utilities
│   │   └── utils/                      # General utilities
│   ├── stores/                         # Zustand state stores
│   │   ├── chatStore.ts                # Chat state management
│   │   └── userStore.ts                # User state management
│   ├── types/                          # TypeScript type definitions
│   ├── tests/                          # Frontend tests
│   ├── next.config.js                  # Next.js configuration
│   ├── tailwind.config.ts              # Tailwind CSS config
│   ├── package.json                    # Frontend dependencies
│   └── .env.local.example              # Frontend environment template
├── docs/                               # Project Documentation
│   ├── ai-context/                     # AI-specific documentation
│   │   ├── project-structure.md        # This file - complete tech stack
│   │   ├── docs-overview.md            # Documentation architecture
│   │   ├── system-integration.md       # Integration patterns
│   │   ├── deployment-infrastructure.md # Infrastructure documentation
│   │   └── handoff.md                  # Task management
│   ├── api/                            # API documentation
│   │   └── openapi.json                # Generated API schema
│   ├── deployment/                     # Deployment guides
│   │   ├── aws-setup.md                # AWS infrastructure setup
│   │   └── ci-cd.md                    # CI/CD pipeline documentation
│   └── development/                    # Development guides
│       ├── setup.md                    # Local development setup
│       └── testing.md                  # Testing guidelines
├── scripts/                            # Automation scripts
│   ├── setup.sh                       # Environment setup script
│   ├── deploy.sh                       # Deployment automation
│   └── maintenance/                    # Maintenance scripts
│       ├── backup.sh                   # Database backup
│       └── migrate.sh                  # Migration runner
├── infrastructure/                     # Infrastructure as Code
│   ├── terraform/                      # Terraform configurations
│   │   ├── main.tf                     # Main infrastructure
│   │   ├── modules/                    # Reusable modules
│   │   │   ├── networking/             # VPC and networking
│   │   │   ├── app_runner/             # App Runner setup
│   │   │   ├── elasticache/            # Redis configuration
│   │   │   └── monitoring/             # CloudWatch setup
│   │   └── environments/               # Environment-specific configs
│   ├── docker/                         # Docker configurations
│   │   ├── backend.dockerfile          # Backend container
│   │   └── docker-compose.prod.yml     # Production compose
│   └── monitoring/                     # Monitoring configurations
│       ├── cloudwatch-dashboards.json  # Custom dashboards
│       └── alerts.yml                  # Alert configurations
├── .github/                            # GitHub Actions workflows
│   └── workflows/
│       ├── ci.yml                      # Continuous integration
│       ├── cd.yml                      # Continuous deployment
│       └── security-scan.yml           # Security scanning
└── .env.example                        # Root environment template
```

## Database Schema (Supabase PostgreSQL)

### Core Tables
```sql
-- Users table (synced with Clerk)
users {
  id: UUID (PK)
  clerk_id: VARCHAR(255) UNIQUE
  email: VARCHAR(255)
  created_at: TIMESTAMP
  updated_at: TIMESTAMP
  preferences: JSONB
  metadata: JSONB
}

-- Chats table
chats {
  id: UUID (PK)
  user_id: UUID (FK → users.id)
  session_id: VARCHAR(255)  -- For anonymous users
  title: VARCHAR(255)
  created_at: TIMESTAMP
  updated_at: TIMESTAMP
  metadata: JSONB
  is_archived: BOOLEAN
}

-- Messages table
messages {
  id: UUID (PK)
  chat_id: UUID (FK → chats.id)
  role: VARCHAR(50) -- 'user', 'assistant', 'system'
  content: TEXT
  metadata: JSONB  -- token count, model used, etc.
  created_at: TIMESTAMP
}

-- RAG context table (for analysis)
rag_contexts {
  id: UUID (PK)
  message_id: UUID (FK → messages.id)
  retrieved_docs: JSONB
  relevance_scores: JSONB
  created_at: TIMESTAMP
}
```

## API Endpoints Structure

### Authentication
- `POST /v1/auth/register` - User registration
- `POST /v1/auth/login` - User login
- `POST /v1/auth/logout` - User logout
- `GET /v1/auth/me` - Get current user

### Chat Management
- `GET /v1/chats` - List user's chats (paginated)
- `POST /v1/chats` - Create new chat
- `GET /v1/chats/{chat_id}` - Get chat details
- `PUT /v1/chats/{chat_id}` - Update chat (title, etc.)
- `DELETE /v1/chats/{chat_id}` - Delete chat
- `POST /v1/chats/{chat_id}/archive` - Archive chat

### Messages
- `GET /v1/chats/{chat_id}/messages` - Get messages (paginated)
- `POST /v1/chats/{chat_id}/messages` - Send message
- `GET /v1/chats/{chat_id}/messages/stream` - SSE stream endpoint

### WebSocket Protocol
- `ws://api.domain.com/ws` - WebSocket connection for real-time streaming
- Message types: auth, message, stream_token, stream_end

## Development Workflow

### Testing Strategy (Testing Pyramid)
- **Unit Tests (70%)**: Business logic, RAG components, utilities
- **Integration Tests (20%)**: API endpoints, database operations, external services
- **E2E Tests (10%)**: Critical user journeys, authentication flow, chat interaction

### Performance Targets
- **API Response Time**: < 200ms for standard endpoints
- **Streaming Latency**: < 100ms first token
- **Database Queries**: < 50ms average
- **Frontend Load Time**: < 3s on 3G networks

### Security Implementation
- **Authentication**: JWT with refresh token rotation
- **Rate Limiting**: Multi-tier (global, authenticated, anonymous, LLM)
- **Input Validation**: Pydantic models (backend) + Zod schemas (frontend)
- **Data Encryption**: TLS 1.3 in transit, encrypted at rest
- **Audit Logging**: All API calls, auth events, data modifications

---

*This comprehensive project structure serves as the authoritative reference for understanding the Eloquent AI chatbot's technical architecture, technology stack, and organizational patterns. All development work should align with these established patterns and standards.*