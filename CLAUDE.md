# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Environment setup
make install-requirements  # Install system dependencies
make install              # Setup Python environment with uv
make docker-run-external-services  # Start MongoDB and RabbitMQ

# Development server (requires external services first)
make docker-run-external-services  # REQUIRED: Start MongoDB and RabbitMQ first
export LINKURATOR_ENVIRONMENT=DEVELOPMENT
export LINKURATOR_VAULT_PASSWORD=$(cat secrets/vault_password.txt)
make run-api              # Start FastAPI server
make run-processor        # Start background processor

# Code quality (ALWAYS run before committing)
make lint                 # MyPy + Ruff linting
make format              # Auto-format code with Ruff
make test                # Run tests (90% coverage required)

# Docker operations
make docker-build
make docker-run-api
make docker-run-processor
```

## Architecture Overview

**Clean Architecture with Domain-Driven Design**
- **Domain** (`/linkurator_core/domain/`): Business entities and core logic
- **Application** (`/linkurator_core/application/`): Use case handlers
- **Infrastructure** (`/linkurator_core/infrastructure/`): External integrations

**Core Domains:**
- **Users**: Authentication, profiles, sessions
- **Subscriptions**: YouTube/Spotify channel management  
- **Items**: Video/podcast content with interactions
- **Topics**: User-defined content categorization

**Key Technologies:**
- FastAPI + Uvicorn/Gunicorn
- MongoDB 5.0.5 with repository pattern
- RabbitMQ for event-driven processing
- Google OAuth + YouTube Data API
- Spotify Web API integration

## Configuration

**Environment Variables:**
- `LINKURATOR_ENVIRONMENT`: DEVELOPMENT or PRODUCTION
- `LINKURATOR_VAULT_PASSWORD`: Required for encrypted config

**Config Files:**
- Development: `/config/app_config_develop.ini`
- Production: `/config/app_config_production.ini.enc` (encrypted)
- Secrets: `/secrets/` (encrypted with vault password)

## Testing

**Structure:**
- Unit tests: `/tests/unit/`
- Integration tests: `/tests/integration/`
- 90% coverage minimum required
- Isolated test database per run

**Running specific tests:**
```bash
pytest tests/unit/domain/users/test_user.py
pytest tests/integration/infrastructure/
```

**Best Practices:**
- Create tests for every feature
- Use mock_factory as much as you can

**Code Quality Standards**

- **Type checking**: MyPy with strict settings
- **Linting**: Ruff with comprehensive rules
- **Line limit**: 120 characters
- **Type annotations**: Required on all functions
- **Import sorting**: Automated with Ruff

## Database

**MongoDB Collections:**
- `users`: User profiles and authentication
- `subscriptions`: YouTube/Spotify channels
- `items`: Video/podcast content
- `topics`: User-defined categories
- `sessions`: User sessions
- `credentials`: OAuth tokens

**Migrations:**
- Located in `/linkurator_core/infrastructure/mongodb/migrations/`
- Run automatically on application start
- Version tracked in database

## API Structure

**FastAPI routers organized by domain:**
- `/linkurator_core/infrastructure/fastapi/routers/`
- OpenAPI docs at `/docs`
- Health check at `/health`
- Cookie-based session authentication

## Background Processing

The processor service handles:
- YouTube subscription updates
- Spotify content fetching
- Email notifications via Gmail
- Event-driven updates via RabbitMQ

Start processor with: `make run-processor`

## External Services

**Required for development:**
- MongoDB 5.0.5 (via Docker)
- RabbitMQ 3.13.0 (via Docker)
- Google OAuth credentials
- Spotify API credentials