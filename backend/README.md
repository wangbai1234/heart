# Heart AI Companion - Backend

Backend API for Heart AI Companion system.

## Architecture

Modular monolith (MVP) → Microservices evolution

**8 Subsystems:**
- **SS01**: Soul (Identity Anchor & Drift Detection)
- **SS02**: Memory (L1-L4 Memory Runtime)
- **SS03**: Emotion (VAD State Machine)
- **SS04**: Relationship (Phase Engine & Stages)
- **SS05**: Composer (Persona Composition Runtime)
- **SS06**: Inner State (Behavior & Proactive Messages)
- **SS07**: Orchestration (Agent Coordination)
- **SS08**: Infrastructure (Data Tier, LLM Providers, Observability)

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL 15+ (with pgvector)
- **Cache**: Redis 7+
- **ORM**: SQLAlchemy 2.0 + Alembic
- **LLM**: Anthropic (Claude), DeepSeek, OpenAI
- **Observability**: Prometheus + OpenTelemetry + structlog

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop
- Make

### Setup

1. **Clone and setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Bootstrap development environment:**
   ```bash
   make bootstrap
   ```
   This will:
   - Start Docker services (PostgreSQL, Redis)
   - Install Python dependencies
   - Run database migrations

3. **Start development server:**
   ```bash
   make dev
   ```

4. **Access API:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/api/docs
   - Health: http://localhost:8000/health/live

## Development

### Common Commands

```bash
# Install dependencies
make install

# Start dev server
make dev

# Run tests
make test
make test-unit
make test-integration

# Lint and format
make lint
make format

# Database migrations
make migrate                # Apply migrations
make migrate-create         # Create new migration
make migrate-rollback       # Rollback last migration

# Docker services
make docker-up              # Start postgres + redis
make docker-up-all          # Start all services (+ MinIO)
make docker-down            # Stop services

# Utilities
make health                 # Check service health
make logs                   # View Docker logs
make db-shell              # PostgreSQL shell
make redis-shell           # Redis CLI
make clean                 # Clean cache files
```

### Project Structure

```
backend/
├── heart/
│   ├── api/                    # FastAPI endpoints
│   ├── ss01_soul/              # Subsystem 01: Soul
│   ├── ss02_memory/            # Subsystem 02: Memory
│   ├── ss03_emotion/           # Subsystem 03: Emotion
│   ├── ss04_relationship/      # Subsystem 04: Relationship
│   ├── ss05_composer/          # Subsystem 05: Composer
│   ├── ss06_inner_state/       # Subsystem 06: Inner State
│   ├── ss07_orchestration/     # Subsystem 07: Orchestration
│   ├── infra/                  # Infrastructure (SS08)
│   ├── workers/                # Background workers
│   ├── safety/                 # Safety & compliance
│   └── utils/                  # Utilities
├── migrations/                 # Alembic migrations
├── tests/                      # Tests
├── pyproject.toml             # Dependencies
└── alembic.ini                # Migration config
```

## Testing

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests (requires Docker services)
make test-integration

# Load tests
make test-load
```

## Database

### Running Migrations

```bash
# Apply all pending migrations
make migrate

# Create a new migration
make migrate-create

# Rollback last migration
make migrate-rollback
```

### Direct Database Access

```bash
# PostgreSQL shell
make db-shell

# Or via psql
psql postgresql://heart:heartdev@localhost:5432/heart
```

## Performance Targets

- **P95 latency**: < 3s (MVP)
- **Throughput**: 1k-10k DAU (MVP)
- **Cost**: ~$1.50/MAU

## Documentation

See `/runtime_specs/` for complete system specifications:
- 00: Runtime Worldview
- 01: Soul Spec
- 02: Memory Runtime
- 03: Emotion State Machine
- 04: Relationship Phase Engine
- 05: Persona Composition
- 06: Inner State & Behavior
- 07: Agent Orchestration
- 08: Engineering Architecture

## License

Proprietary
