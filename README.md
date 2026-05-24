# Heart (心屿) - AI Companion Project

An emotionally authentic AI companion system built on 8 specialized subsystems.

> 🚨 **新 AI session 必读**：[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — 当前 phase / blocker / 下一步。
> 文档导航：[`docs/README.md`](docs/README.md)。历史归档：[`archive/`](archive/)。

## Project Overview

Heart is an AI companion platform designed to create deep, emotionally authentic relationships between users and AI characters. The system implements sophisticated memory, emotion, and relationship modeling to deliver natural, coherent character interactions.

## Architecture

### Modular Monolith → Microservices Evolution

**MVP Phase**: Single Python application with 8 subsystem modules
**V1 Phase**: Critical services extracted (LLM, Memory, Inner Loop)
**V2 Phase**: Full microservices architecture

### 8 Core Subsystems

1. **SS01 - Soul**: Identity anchor & drift detection
2. **SS02 - Memory**: 4-layer memory system (L1-L4)
3. **SS03 - Emotion**: VAD emotion state machine
4. **SS04 - Relationship**: Phase-based relationship engine
5. **SS05 - Composer**: Multi-layer persona composition
6. **SS06 - Inner State**: Autonomous behavior & proactive messages
7. **SS07 - Orchestration**: Agent coordination & safety
8. **SS08 - Infrastructure**: Data tier & deployment

## Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL 15+ (with pgvector)
- **Cache**: Redis 7+
- **ORM**: SQLAlchemy 2.0 + Alembic

### Infrastructure
- **Container**: Docker
- **Orchestration**: Kubernetes 1.28+ (Production)
- **Observability**: Prometheus + Grafana + OpenTelemetry
- **LLM Providers**: Anthropic (Claude), DeepSeek, OpenAI

## Quick Start

### Prerequisites
- Python 3.11+
- Docker Desktop
- Make (optional, for convenience)

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: ANTHROPIC_API_KEY, DEEPSEEK_API_KEY
```

### 2. Bootstrap Development Environment

```bash
# Start services and run migrations
make bootstrap
```

This command will:
- Start PostgreSQL (with pgvector) and Redis via Docker
- Install Python dependencies
- Run database migrations

### 3. Start Development Server

```bash
make dev
```

Access the API at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/api/docs
- **Health**: http://localhost:8000/health/live

## Development

### Common Commands

```bash
# Development
make dev                    # Start dev server
make test                   # Run all tests
make lint                   # Lint code
make format                 # Format code

# Database
make migrate                # Apply migrations
make migrate-create         # Create new migration
make db-shell              # PostgreSQL shell

# Docker
make docker-up             # Start postgres + redis
make docker-down           # Stop services
make logs                  # View logs

# Utilities
make health                # Check service health
make clean                 # Clean cache files
```

### Project Structure

```
heart/
├── backend/                    # Backend API
│   ├── heart/
│   │   ├── api/               # FastAPI endpoints
│   │   ├── ss01_soul/         # Subsystem 01: Soul
│   │   ├── ss02_memory/       # Subsystem 02: Memory
│   │   ├── ss03_emotion/      # Subsystem 03: Emotion
│   │   ├── ss04_relationship/ # Subsystem 04: Relationship
│   │   ├── ss05_composer/     # Subsystem 05: Composer
│   │   ├── ss06_inner_state/  # Subsystem 06: Inner State
│   │   ├── ss07_orchestration/# Subsystem 07: Orchestration
│   │   ├── infra/             # Infrastructure (SS08)
│   │   ├── workers/           # Background workers
│   │   ├── safety/            # Safety & compliance
│   │   └── utils/             # Utilities
│   ├── migrations/            # Database migrations
│   ├── tests/                 # Tests
│   └── pyproject.toml        # Dependencies
│
├── runtime_specs/             # System specifications
│   ├── 00_runtime_worldview.md
│   ├── 01_identity_anchor_soul_spec.md
│   ├── 02_memory_runtime.md
│   ├── 03_emotion_state_machine.md
│   ├── 04_relationship_phase_engine.md
│   ├── 05_persona_composition_runtime.md
│   ├── 06_inner_state_behavior_runtime.md
│   ├── 07_agent_orchestration.md
│   └── 08_engineering_architecture.md
│
├── soul_specs/                # Character definitions (future)
├── config/                    # System configuration (future)
├── infra/                     # IaC (future)
├── docker-compose.yml         # Local development
├── .env.example              # Environment template
└── Makefile                  # Development commands
```

## Documentation

### Runtime Specifications

Complete system design documents in `/runtime_specs/`:

- **00**: Runtime Worldview - Overall system philosophy
- **01**: Soul Spec - Character identity system
- **02**: Memory Runtime - 4-layer memory architecture
- **03**: Emotion State Machine - VAD emotion model
- **04**: Relationship Phase Engine - Relationship dynamics
- **05**: Persona Composition - Response generation
- **06**: Inner State & Behavior - Autonomous actions
- **07**: Agent Orchestration - System coordination
- **08**: Engineering Architecture - **Implementation guide** ← Start here

### API Documentation

Once the server is running, access interactive API docs at:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Performance Targets

### MVP Phase (0-10k DAU)
- **P95 latency**: < 3s
- **Cost**: ~$1.50/MAU
- **Infrastructure**: Single region, modular monolith

### V1 Phase (10k-100k DAU)
- **P95 latency**: < 2.5s
- **Cost**: ~$1.20/MAU (with optimizations)
- **Infrastructure**: Multi-region, critical services extracted

### V2 Phase (100k-1M DAU)
- **P95 latency**: < 2s
- **Cost**: ~$0.50/MAU (with Companion-LLM)
- **Infrastructure**: Full microservices, self-hosted inference

## Testing

```bash
# 推荐：本地一键跑全部基础检查（lint + unit-tests + schema-validation）
bash scripts/ci.sh

# 单独 stage
bash scripts/ci.sh lint
bash scripts/ci.sh unit-tests
bash scripts/ci.sh integration-tests   # opt-in，需 postgres + redis + DEEPSEEK_API_KEY

# Makefile 入口（与 ci.sh 互补，需 docker 服务）
make test
make test-unit
make test-integration
```

## Deployment

### Local Development
- Docker Compose (PostgreSQL + Redis)
- Python dev server (uvicorn)

### Production (Future)
- Kubernetes cluster
- Managed PostgreSQL (RDS)
- Managed Redis (ElastiCache)
- Multi-region deployment

## Cost Model

**MVP Target**: $1.50/MAU

Breakdown:
- **LLM calls**: ~$1.00 (largest component)
- **Compute**: ~$0.05
- **Database**: ~$0.05
- **Cache**: ~$0.02
- **Storage**: ~$0.01
- **Other**: ~$0.37

## Contributing

See `/runtime_specs/08_engineering_architecture.md` Appendix E for implementation guidelines.

### Key Principles
- Follow subsystem specifications strictly
- No cross-user data access
- All LLM calls through Model Router
- Idempotent operations
- Backwards-compatible migrations

## License

Proprietary

## Contact

For questions or support, refer to the runtime specifications or implementation guide.
