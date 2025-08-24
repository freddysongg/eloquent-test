# Eloquent AI - Documentation Architecture & Navigation Guide

This document serves as the comprehensive navigation guide for the Eloquent AI chatbot project documentation system. **All developers and AI agents should start here to understand the project's complete documentation structure and quickly locate the information needed for specific tasks.**

## Project Overview & Business Context

**Vision**: AI-powered chatbot with retrieval-augmented generation (RAG) for accurate, context-aware responses to fintech FAQ queries.

**Architecture**: Full-stack web application with Next.js frontend, FastAPI backend, and integrated AI/RAG pipeline using Pinecone vector database and Claude API.

**Business Domain**: Fintech company FAQ bot covering Account & Registration, Payments & Transactions, Security & Fraud Prevention, Regulations & Compliance, and Technical Support.

## Documentation Philosophy

This project uses an **evidence-based, AI-first documentation system** designed for:
- **Efficient Context Loading**: Hierarchical organization for targeted AI context injection
- **Cross-Component Understanding**: Integration patterns and system-wide architectural decisions
- **Practical Implementation**: Real-world examples, configuration files, and actionable guidance
- **Scalable Knowledge Management**: Documentation that evolves with the codebase

## Core Documentation Structure

### 📋 Essential Foundation (Start Here)

**Every AI agent and developer MUST read these first:**

- **[Master Context](/CLAUDE.md)** - *Essential for every session*  
  Project coding standards, security requirements, MCP server integrations, and development protocols. Contains multi-agent workflows and automatic context injection rules.

- **[Project Structure](/docs/ai-context/project-structure.md)** - *REQUIRED before any coding*  
  Complete technology stack, file organization, and system architecture. **Must be referenced for Gemini consultations and technical decisions.**

### 🔧 System-Wide Architecture & Integration

**For cross-component work and system understanding:**

- **[System Integration](/docs/ai-context/system-integration.md)** - *Cross-component patterns*  
  End-to-end data flows, external service integrations (Pinecone, Claude, Clerk), RAG pipeline architecture, authentication flows, WebSocket communication, caching strategies, and error handling patterns.

- **[Deployment Infrastructure](/docs/ai-context/deployment-infrastructure.md)** - *Production deployment*  
  AWS infrastructure architecture, Terraform IaC, Docker containerization, CI/CD pipelines, monitoring setup, scaling strategies, cost optimization, and deployment best practices.

### 📊 Project Management & Continuity

**For session continuity and project tracking:**

- **[Orchestrator Task Framework](/docs/ai-context/orchestrator-task-framework.md)** - *AI orchestration system*  
  Comprehensive 5-phase development framework for orchestrator agents with specialized sub-agent delegation, task templates, progress tracking, and quality gates. Essential for multi-agent project management and structured development workflows.

- **[Task Management](/docs/ai-context/handoff.md)** - *Session continuity*  
  Current development progress, active tasks, documentation system evolution, and next session handoff protocols.

## Component-Level Documentation

### 🖥️ Backend Components

**FastAPI-based backend application with AI/RAG integration:**

- **[Backend Context](/backend/CONTEXT.md)** - *Server implementation*  
  FastAPI patterns, SQLAlchemy models, Pydantic schemas, service architecture, repository patterns, and performance optimization strategies.

### 🌐 Frontend Components

**Next.js-based web application with real-time chat interface:**

- **[Frontend Context](/frontend/CONTEXT.md)** - *Client implementation*  
  Next.js App Router patterns, TypeScript components, Tailwind CSS + Shadcn/ui styling, Zustand state management, React Query integration, and WebSocket communication.

### 🏗️ Infrastructure Components

**Production-ready AWS infrastructure with IaC:**

- **[Infrastructure Code](/infrastructure/CONTEXT.md)** - *Infrastructure as Code*  
  Terraform modules, AWS App Runner configuration, ElastiCache Redis setup, API Gateway configuration, and CloudWatch monitoring patterns.

## Feature-Specific Documentation

**Detailed documentation co-located with code for specific implementation patterns:**

### 🔧 Backend Feature Areas

**When working on specific backend features, reference these targeted contexts:**

- **[API Layer](/backend/app/api/CONTEXT.md)** - *REST API patterns*  
  FastAPI endpoint design, Pydantic schemas, middleware implementation, dependency injection, and request/response handling patterns.

- **[Core Services](/backend/app/services/CONTEXT.md)** - *Business logic patterns*  
  Service orchestration, RAG pipeline integration, chat management, streaming responses, authentication services, and error handling.

- **[Data Models](/backend/app/models/CONTEXT.md)** - *Data patterns*  
  SQLAlchemy models, database schemas, relationships, migrations, and data access patterns.

- **[RAG Pipeline](/backend/app/rag/CONTEXT.md)** - *AI/ML integration patterns*  
  Pinecone vector search, document retrieval, context management, reranking algorithms, and Claude API integration.

- **[WebSocket Handling](/backend/app/websocket/CONTEXT.md)** - *Real-time patterns*  
  Connection management, message broadcasting, Redis pub/sub integration, and streaming response handling.

### 🎨 Frontend Feature Areas

**When working on specific frontend features, reference these targeted contexts:**

- **[Chat Interface](/frontend/components/chat/CONTEXT.md)** - *Chat UI patterns*  
  Real-time message display, streaming response handling, WebSocket integration, message input handling, and chat history management.

- **[UI Components](/frontend/components/ui/CONTEXT.md)** - *Design system patterns*  
  Shadcn/ui component usage, Tailwind CSS patterns, accessibility implementation, responsive design, and component composition.

- **[State Management](/frontend/stores/CONTEXT.md)** - *Client state patterns*  
  Zustand store patterns, React Query integration, WebSocket state management, and persistent storage handling.

- **[API Integration](/frontend/lib/api/CONTEXT.md)** - *Client-server patterns*  
  HTTP client setup, error handling, authentication token management, and response caching strategies.

- **[Custom Hooks](/frontend/hooks/CONTEXT.md)** - *React patterns*  
  Chat management hooks, WebSocket connection hooks, authentication hooks, and reusable stateful logic.



## 🎯 Quick Reference for Common Tasks

### 🤖 For AI Agents - When to Read Which Documents

**Starting any new session:**
1. Read [Master Context](/CLAUDE.md) - coding standards and project patterns
2. Read [Project Structure](/docs/ai-context/project-structure.md) - tech stack and architecture
3. Check [Task Management](/docs/ai-context/handoff.md) - current project status

**For orchestrator agents managing development:**
- Read [Orchestrator Task Framework](/docs/ai-context/orchestrator-task-framework.md) - comprehensive 5-phase development management system with sub-agent delegation patterns

**For cross-component work:**
- Read [System Integration](/docs/ai-context/system-integration.md) - data flows and service integrations
- Review component-specific CONTEXT.md files for affected areas

**For infrastructure work:**
- Read [Deployment Infrastructure](/docs/ai-context/deployment-infrastructure.md) - AWS setup and CI/CD
- Review [System Integration](/docs/ai-context/system-integration.md) for service dependencies

**For Gemini consultations:**
- **Always attach**: [Project Structure](/docs/ai-context/project-structure.md)
- **Include relevant**: Feature-specific CONTEXT.md files for the area being worked on

### 👨‍💻 For Developers - Common Development Scenarios

**Setting up local development:**
1. [Project Structure](/docs/ai-context/project-structure.md) - understand tech stack
2. [Master Context](/CLAUDE.md) - development environment and tools
3. [Backend Context](/backend/CONTEXT.md) and [Frontend Context](/frontend/CONTEXT.md) - setup instructions

**Working on the RAG pipeline:**
1. [System Integration](/docs/ai-context/system-integration.md) - RAG architecture overview
2. [RAG Pipeline](/backend/app/rag/CONTEXT.md) - implementation details
3. [Core Services](/backend/app/services/CONTEXT.md) - service integration patterns

**Implementing new API endpoints:**
1. [API Layer](/backend/app/api/CONTEXT.md) - API patterns and conventions
2. [Data Models](/backend/app/models/CONTEXT.md) - database schema patterns
3. [System Integration](/docs/ai-context/system-integration.md) - authentication and validation

**Building chat interface features:**
1. [Chat Interface](/frontend/components/chat/CONTEXT.md) - chat UI patterns
2. [WebSocket Handling](/backend/app/websocket/CONTEXT.md) - real-time communication
3. [State Management](/frontend/stores/CONTEXT.md) - client state patterns

**Deployment and infrastructure changes:**
1. [Deployment Infrastructure](/docs/ai-context/deployment-infrastructure.md) - full infrastructure setup
2. [Infrastructure Code](/infrastructure/CONTEXT.md) - Terraform patterns
3. [System Integration](/docs/ai-context/system-integration.md) - service dependencies

## 📈 Performance Targets & Quality Standards

**Response Time Targets:**
- API endpoints: < 200ms standard, < 100ms streaming first token
- Database queries: < 50ms average
- Frontend load time: < 3s on 3G networks
- WebSocket latency: < 100ms for real-time messaging

**Quality Standards:**
- Test coverage: ≥80% unit tests, ≥70% integration tests
- Type coverage: 100% TypeScript/Python type hints required
- Security: TLS 1.3, input validation, audit logging, rate limiting
- Accessibility: WCAG 2.1 AA compliance minimum

**Architecture Principles:**
- SOLID principles for all code organization
- DRY, KISS, YAGNI for development approach
- Evidence-based decision making with metrics
- Security-first design with defense in depth

## 🔄 Documentation Maintenance

### Adding New Documentation

**New Component Documentation:**
1. Create `/component/CONTEXT.md` with implementation patterns
2. Update this overview document with new component entry
3. Link from relevant integration documents

**New Feature Documentation:**
1. Create feature-specific CONTEXT.md in appropriate directory
2. Reference parent component patterns and conventions
3. Update this overview if it represents a new functional area

**Updating Existing Documentation:**
1. Maintain backward compatibility with existing references
2. Update cross-references when moving or restructuring content
3. Archive obsolete documentation rather than deleting immediately

### Quality Assurance

**Documentation Standards:**
- Use clear, actionable language optimized for AI consumption
- Include practical examples and configuration snippets
- Maintain consistent terminology throughout all documents
- Structure information hierarchically with clear headings

**Review Process:**
- Technical accuracy verified by domain experts
- AI agent usability tested through actual development scenarios
- Regular reviews for outdated information and broken references
- Integration with code review process for documentation updates

---

**📌 Remember**: This documentation system is designed for both human developers and AI agents. When in doubt, prioritize clarity and actionable information over brevity. Every piece of context should help make better decisions and write better code.