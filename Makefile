.PHONY: help dev test lint migrate clean install docker-up docker-down check-mvp test-e2e

# Default target
help:
	@echo "Heart AI Companion - Backend Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install Python dependencies"
	@echo "  dev          - Start development server"
	@echo "  test         - Run tests"
	@echo "  test-e2e     - Run end-to-end tests (real uvicorn + PG + Playwright)"
	@echo "  lint         - Run linters (ruff, mypy)"
	@echo "  migrate      - Run database migrations"
	@echo "  docker-up    - Start Docker services (postgres, redis)"
	@echo "  docker-down  - Stop Docker services"
	@echo "  check-mvp    - Run MVP gate check (10 gates)"
	@echo "  clean        - Clean cache and temp files"

# Install dependencies
install:
	@echo "Installing dependencies..."
	cd backend && pip install -e ".[dev]"

# Start development server
dev:
	@echo "Starting development server..."
	cd backend && uvicorn heart.api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	@echo "Running tests..."
	cd backend && pytest -v --cov=heart --cov-report=term-missing

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	cd backend && pytest tests/unit -v

# Run integration tests
# Run contract tests (Tier A)
test-contract:
	@echo "Running contract tests..."
	cd backend && pytest -m contract tests/contract -v

# Run integration tests (Tier B)
test-integration:
	@echo "Running integration tests..."
	cd backend && pytest -m integration tests/integration -v

# Run live tests (Tier C) — requires --live flag + DEEPSEEK_API_KEY
test-live:
	@echo "Running live tests (real DeepSeek)..."
	cd backend && pytest -m live --live tests/live -v

# Run end-to-end tests (Tier E) — real uvicorn + real PG + Playwright APIRequestContext
test-e2e:
	@echo "Running end-to-end tests (real uvicorn + PG)..."
	@echo "Checking docker services..."
	@docker compose ps postgres 2>/dev/null | grep -q "Up" || (echo "Starting postgres/redis..." && docker compose up -d postgres redis)
	@echo "Checking migrations..."
	cd backend && alembic current | grep -q "head" || alembic upgrade head
	cd backend && pytest tests/e2e -m e2e -v

# Run load tests
test-load:
	@echo "Running load tests..."
	cd backend && locust -f tests/load/turn.py --headless -u 10 -r 2 -t 60s

# Lint code
lint:
	@echo "Running ruff..."
	cd backend && ruff check heart tests
	@echo "Running mypy..."
	cd backend && mypy heart

# Format code
format:
	@echo "Formatting code with ruff..."
	cd backend && ruff format heart tests

# Run database migrations
migrate:
	@echo "Running migrations..."
	cd backend && alembic upgrade head

# Create a new migration
migrate-create:
	@echo "Creating new migration..."
	@read -p "Enter migration message: " msg; \
	cd backend && alembic revision --autogenerate -m "$$msg"

# Rollback last migration
migrate-rollback:
	@echo "Rolling back last migration..."
	cd backend && alembic downgrade -1

# Start Docker services
docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d postgres redis

# Start all Docker services (including MinIO + monitoring)
docker-up-all:
	@echo "Starting all Docker services..."
	docker-compose --profile storage --profile monitoring up -d

# Bring up the full local stack (DB + Redis + Prometheus + Grafana)
up:
	@echo "Bringing up full Heart local stack..."
	docker-compose --profile monitoring up -d postgres redis prometheus grafana
	@echo ""
	@echo "Services:"
	@echo "  API:        http://localhost:8000"
	@echo "  Grafana:    http://localhost:3000 (admin / admin)"
	@echo "  Prometheus: http://localhost:9090"
	@echo ""
	@echo "Run 'make dev' in another terminal to start the API server."

# Stop Docker services
docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

# Clean cache and temp files
clean:
	@echo "Cleaning cache and temp files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Bootstrap development environment
bootstrap: docker-up install
	@echo "Waiting for services to be ready..."
	sleep 5
	@echo "Running migrations..."
	$(MAKE) migrate
	@echo ""
	@echo "✅ Bootstrap complete!"
	@echo "Run 'make dev' to start the development server"

# Check if services are healthy
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health/live | jq . || echo "API not running"
	@docker-compose ps

# View logs
logs:
	docker-compose logs -f

# Shell into postgres
db-shell:
	docker-compose exec postgres psql -U heart -d heart

# Shell into redis
redis-shell:
	docker-compose exec redis redis-cli

# ── Voice Drift Regression (Phase 7 §1.4) ──
voice-baseline: ## Generate voice baseline (HUMAN-triggered, uses real LLM)
	@if [ -z "$(CHARACTER)" ]; then \
		echo "Usage: make voice-baseline CHARACTER={rin,dorothy,all}"; \
		echo "  e.g. make voice-baseline CHARACTER=rin"; \
		exit 1; \
	fi
	cd backend && python3 scripts/run_voice_drift.py generate-baseline --character $(CHARACTER)

voice-regress: ## Run voice drift regression (uses real LLM, requires baseline)
	@if [ -z "$(CHARACTER)" ]; then \
		echo "Usage: make voice-regress CHARACTER={rin,dorothy,all}"; \
		echo "  e.g. make voice-regress CHARACTER=rin"; \
		exit 1; \
	fi
	cd backend && python3 -m pytest tests/live/test_voice_drift.py --live -v -k $(CHARACTER)

voice-report: ## Regenerate HTML drift report
	cd backend && python3 scripts/run_voice_drift.py report --scores $(SCORES) --character $(CHARACTER) --output $(OUTPUT)

# ── Demo Seed Loader ──
seed-demo: ## Populate DB with demo state for alice×rin + bob×dorothy (idempotent)
	cd backend && python3 heart/scripts/seed_demo.py

reset-demo: ## Drop demo users and reseed
	cd backend && python3 heart/scripts/seed_demo.py --reset

# ── MVP Gate Check ──
check-mvp: ## Run 10-gate MVP readiness check
	cd backend && python3 scripts/check_mvp.py
