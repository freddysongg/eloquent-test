# Eloquent AI - Development and Deployment Commands
.PHONY: help install dev build test clean deploy stop logs

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Eloquent AI - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Development Commands
install: ## Install all dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	cd backend && poetry install
	cd frontend && npm install

dev: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose up --build

dev-detached: ## Start development environment in background
	@echo "$(BLUE)Starting development environment (detached)...$(NC)"
	docker-compose up -d --build

# Build Commands
build: ## Build all services for production
	@echo "$(BLUE)Building production images...$(NC)"
	docker-compose -f docker-compose.prod.yml build

build-backend: ## Build backend service only
	@echo "$(BLUE)Building backend service...$(NC)"
	docker build -t eloquent-backend ./backend

build-frontend: ## Build frontend service only
	@echo "$(BLUE)Building frontend service...$(NC)"
	docker build -t eloquent-frontend ./frontend

# Testing Commands
test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	$(MAKE) test-backend
	$(MAKE) test-frontend

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	cd backend && poetry run pytest -v

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && npm test

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	cd backend && poetry run pytest --cov=app --cov-report=html
	cd frontend && npm run test:coverage

# Code Quality Commands
lint: ## Run linting on all code
	@echo "$(BLUE)Running linters...$(NC)"
	cd backend && poetry run black --check app/ && poetry run isort --check-only app/ && poetry run mypy app/
	cd frontend && npm run lint

format: ## Format all code
	@echo "$(BLUE)Formatting code...$(NC)"
	cd backend && poetry run black app/ && poetry run isort app/
	cd frontend && npm run format

type-check: ## Run type checking
	@echo "$(BLUE)Running type checks...$(NC)"
	cd backend && poetry run mypy app/
	cd frontend && npm run type-check

# Database Commands
db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	cd backend && poetry run alembic upgrade head

db-reset: ## Reset database (WARNING: Destructive)
	@echo "$(RED)Resetting database...$(NC)"
	@read -p "Are you sure? This will delete all data (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose down -v
	docker-compose up -d postgres redis
	sleep 5
	$(MAKE) db-migrate

# Production Commands
deploy-prod: ## Deploy to production
	@echo "$(BLUE)Deploying to production...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d --build

deploy-staging: ## Deploy to staging
	@echo "$(BLUE)Deploying to staging...$(NC)"
	docker-compose -f docker-compose.yml up -d --build
	docker-compose logs -f

# Monitoring Commands
logs: ## Show logs for all services
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-frontend: ## Show frontend logs
	docker-compose logs -f frontend

logs-db: ## Show database logs
	docker-compose logs -f postgres

monitoring: ## Start with monitoring stack
	@echo "$(BLUE)Starting with monitoring...$(NC)"
	docker-compose --profile monitoring -f docker-compose.prod.yml up -d

# Maintenance Commands
stop: ## Stop all services
	@echo "$(BLUE)Stopping all services...$(NC)"
	docker-compose down

stop-prod: ## Stop production services
	@echo "$(BLUE)Stopping production services...$(NC)"
	docker-compose -f docker-compose.prod.yml down

clean: ## Clean up Docker resources
	@echo "$(BLUE)Cleaning up Docker resources...$(NC)"
	docker-compose down -v --remove-orphans
	docker system prune -f

clean-all: ## Clean everything (WARNING: Removes all data)
	@echo "$(RED)Cleaning all Docker resources and data...$(NC)"
	@read -p "This will remove ALL Docker data. Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose down -v --remove-orphans
	docker system prune -a -f
	docker volume prune -f

# Health Checks
health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo "$(GREEN)Backend:$(NC)"
	@curl -f http://localhost:8000/health 2>/dev/null && echo " ✓ Healthy" || echo " ✗ Unhealthy"
	@echo "$(GREEN)Frontend:$(NC)"
	@curl -f http://localhost:3000/api/health 2>/dev/null && echo " ✓ Healthy" || echo " ✗ Unhealthy"
	@echo "$(GREEN)Database:$(NC)"
	@docker-compose exec -T postgres pg_isready 2>/dev/null && echo " ✓ Healthy" || echo " ✗ Unhealthy"
	@echo "$(GREEN)Redis:$(NC)"
	@docker-compose exec -T redis redis-cli ping 2>/dev/null && echo " ✓ Healthy" || echo " ✗ Unhealthy"

# Backup and Restore
backup: ## Backup database
	@echo "$(BLUE)Creating database backup...$(NC)"
	mkdir -p backup
	docker-compose exec -T postgres pg_dump -U $${POSTGRES_USER:-eloquent} $${POSTGRES_DB:-eloquent_ai} > backup/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup created in backup/ directory$(NC)"

restore: ## Restore database from backup
	@echo "$(BLUE)Restoring database...$(NC)"
	@read -p "Enter backup filename: " backup_file && \
	docker-compose exec -T postgres psql -U $${POSTGRES_USER:-eloquent} -d $${POSTGRES_DB:-eloquent_ai} < backup/$$backup_file

# Development Utilities
shell-backend: ## Open backend shell
	docker-compose exec backend /bin/bash

shell-frontend: ## Open frontend shell
	docker-compose exec frontend /bin/sh

shell-db: ## Open database shell
	docker-compose exec postgres psql -U $${POSTGRES_USER:-eloquent} -d $${POSTGRES_DB:-eloquent_ai}

shell-redis: ## Open Redis CLI
	docker-compose exec redis redis-cli

# Environment Management
env-copy: ## Copy environment template
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)Environment file created from template$(NC)"; \
		echo "$(YELLOW)Please update .env with your configuration$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists$(NC)"; \
	fi

env-check: ## Check environment variables
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	@cd backend && poetry run python -c "from app.core.config import settings; print('✓ Backend config loaded')"
	@echo "$(GREEN)Environment configuration is valid$(NC)"

# Performance Testing
load-test: ## Run basic load test (requires Apache Bench)
	@echo "$(BLUE)Running load test...$(NC)"
	@if command -v ab > /dev/null; then \
		ab -n 1000 -c 10 http://localhost:8000/health; \
	else \
		echo "$(RED)Apache Bench (ab) not found. Install with: apt-get install apache2-utils$(NC)"; \
	fi