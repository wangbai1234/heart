.PHONY: help dev test lint migrate clean install docker-up docker-down

# Default target
help:
	@echo "Heart AI Companion - Backend Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install Python dependencies"
	@echo "  dev          - Start development server"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linters (ruff, mypy)"
	@echo "  migrate      - Run database migrations"
	@echo "  docker-up    - Start Docker services (postgres, redis)"
	@echo "  docker-down  - Stop Docker services"
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
test-integration:
	@echo "Running integration tests..."
	cd backend && pytest tests/integration -v

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

# Start all Docker services (including MinIO)
docker-up-all:
	@echo "Starting all Docker services..."
	docker-compose --profile storage up -d

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
