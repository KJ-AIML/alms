# 07 - Setup & Installation

> **Last Updated:** June 16, 2026  
> **Version:** 0.3.0  
> **Status:** ✅ Active

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.13+ | Programming language |
| PostgreSQL | 15+ | Database (optional for local dev) |
| Redis | 7+ | Cache (optional) |
| Git | Latest | Version control |

### Optional Software

| Software | Purpose |
|----------|---------|
| Docker | Containerization |
| Docker Compose | Multi-service orchestration |

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/KJ-AIML/alms.git
cd alms
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env  # or use your preferred editor
```

### 3. Install Dependencies

#### Using UV (Recommended)

```bash
# Install uv if not already installed
# Windows (PowerShell):
irm https://astral.sh/uv/install.ps1 | iex

# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

#### Using pip (Alternative)

```bash
# Create virtual environment
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 4. Run Database Migrations (Optional)

If using PostgreSQL:

```bash
# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 5. Start the Application

```bash
# Using uv (recommended)
uv run -m src.api.main

# Using Python
python -m src.api.main
```

The API will be available at:
- **API:** http://localhost:3000
- **Documentation:** http://localhost:3000/docs

## Environment Variables

### Feature Flags

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_ENABLED` | Enable AI agents and LangGraph workflows | `False` |
| `DATABASE_ENABLED` | Enable database connection and readiness check | `True` |
| `REDIS_ENABLED` | Enable Redis dependency | `False` |
| `MODEL_PROVIDER` | AI provider selection (`openai`; Google/Anthropic deferred) | `openai` |

### AI (Required only when `AI_ENABLED=True`)

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |

### Database (Optional for local dev)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_HOST` | Database host | `localhost` |
| `DATABASE_PORT` | Database port | `5432` |
| `DATABASE_NAME` | Database name | `db` |
| `DATABASE_USER` | Database user | `postgres` |
| `DATABASE_PASSWORD` | Database password | `postgres` |

### AI Models (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_MODEL_BASIC` | Default chat model | `gpt-4o-mini` |
| `OPENAI_MODEL_REASONING` | Reasoning model | `gpt-4o` |
| `GOOGLE_API_KEY` | Google AI key | `None` |
| `GOOGLE_MODEL_BASIC` | Google default model | `None` |

### Server (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVER_HOST` | Server bind host | `0.0.0.0` |
| `SERVER_PORT` | Server port | `3000` |
| `DEBUG` | Debug mode | `False` |
| `LOG_LEVEL` | Logging level | `info` |

### Security (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | App secret key | `your-default-secret-key` |
| `X_API_KEY` | API key for endpoints | `your-api-key-here` |
| `ALLOWED_HOSTS` | CORS allowed hosts | `*` |

> **Production fail-fast:** When `DEBUG=False`, ALMS calls `validate_production_settings()` at startup and refuses to start if `SECRET_KEY` is still the default placeholder or `ALLOWED_HOSTS` contains `*`. Change both before deploying.

### Cache (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_PASSWORD` | Redis password | `None` |
| `REDIS_DB` | Redis database | `0` |
| `CACHE_TTL` | Cache TTL (seconds) | `900` |

### Example .env file

```bash
# Feature flags
AI_ENABLED=False
DATABASE_ENABLED=True
REDIS_ENABLED=False
MODEL_PROVIDER=openai

# AI keys — required only when AI_ENABLED=True
OPENAI_API_KEY=sk-your-openai-key-here

# AI Models
OPENAI_MODEL_BASIC=gpt-4o-mini
OPENAI_MODEL_REASONING=gpt-4o

# Database (optional for local dev)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=alms_db
DATABASE_USER=postgres
DATABASE_PASSWORD=your-db-password

# Server
DEBUG=true
LOG_LEVEL=debug
SERVER_PORT=3000

# Security
SECRET_KEY=your-super-secret-key

# Cache
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Development Setup

### Using Docker (Recommended for Team Development)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Run migrations
docker-compose exec app alembic upgrade head

# Stop services
docker-compose down
```

### Database Setup

#### Option 1: Docker PostgreSQL (Recommended)

```bash
# Start PostgreSQL
docker run -d \
  --name alms-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=alms_db \
  -p 5432:5432 \
  postgres:15-alpine

# Set DATABASE_URL in .env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/alms_db
```

#### Option 2: Local PostgreSQL

```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt-get install postgresql-15
sudo service postgresql start

# Create database
createdb alms_db
```

#### Option 3: SQLite (Development Only)

```bash
# Set in .env
DATABASE_URL=sqlite+aiosqlite:///./dev.db
```

⚠️ **Note:** SQLite doesn't support all PostgreSQL features. Use only for simple development.

### Redis Setup (Optional)

```bash
# Using Docker
docker run -d \
  --name alms-redis \
  -p 6379:6379 \
  redis:7-alpine

# Or local install
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server
```

## Available Scripts

### Development

| Script | Description |
|--------|-------------|
| `uv run -m src.api.main` | Run development server |
| `uv run pytest src/tests` | Run all tests |
| `uv run pytest src/tests -v` | Run tests with verbose output |
| `uv run pytest src/tests/v1/ -v` | Run v1 tests only |

### Database

| Script | Description |
|--------|-------------|
| `alembic revision --autogenerate -m "desc"` | Create migration |
| `alembic upgrade head` | Apply all migrations |
| `alembic downgrade -1` | Rollback one migration |
| `alembic current` | Show current version |
| `alembic history` | Show migration history |

### Code Quality

| Script | Description |
|--------|-------------|
| `ruff check src/` | Check code style |
| `ruff check --fix src/` | Fix auto-fixable issues |
| `ruff format src/` | Format code |

### Dependencies

| Script | Description |
|--------|-------------|
| `uv sync` | Sync dependencies |
| `uv lock` | Update lock file |
| `uv add <package>` | Add production dependency |
| `uv add --dev <package>` | Add dev dependency |
| `uv tree` | Show dependency tree |

## IDE Setup

### VS Code

**Recommended Extensions:**
- Python (Microsoft)
- Ruff (Astral)
- Python Type Hint
- Thunder Client (API testing)

**Settings (.vscode/settings.json):**
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "charliermarsh.ruff",
  "ruff.organizeImports": true,
  "ruff.fixAll": true
}
```

### PyCharm

1. Set Python interpreter to `.venv/bin/python`
2. Enable Ruff integration (Settings → Tools → External Tools)
3. Configure Black/Ruff as formatter

## Project Structure Overview

```
alms/
├── src/                    # Source code
│   ├── api/               # API Layer (FastAPI)
│   ├── execution/         # Execution Layer (business logic)
│   ├── agents/            # Agent Layer (AI logic)
│   ├── providers/         # Providers Layer
│   ├── database/          # Database Layer
│   ├── core/              # Shared Core
│   ├── config/            # Configuration
│   ├── models/            # Domain models
│   ├── tests/             # Automated tests
│   └── utils/             # Utilities
├── docs/                  # Documentation
├── alembic/              # Database migrations
├── rules/                # Project rules
├── .env                  # Environment variables
├── pyproject.toml        # Dependencies
└── README.md             # Project overview
```

## Troubleshooting

### Common Issues

#### 1. UV Not Found

```bash
# Reinstall uv
# Windows (PowerShell):
irm https://astral.sh/uv/install.ps1 | iex

# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal
```

#### 2. Import Errors

```bash
# Ensure uv sync completed
uv sync

# Check Python version (must be 3.13+)
python --version

# Verify virtual environment
which python  # Should point to .venv
```

#### 3. Database Connection Failed

```bash
# Check PostgreSQL is running
docker ps  # If using Docker

# Verify connection string
cat .env | grep DATABASE

# Test connection manually
psql postgresql://postgres:postgres@localhost:5432/alms_db
```

#### 4. Alembic Migration Errors

```bash
# Reset migrations (DEVELOPMENT ONLY)
alembic downgrade base
alembic upgrade head

# Or delete and recreate
rm -rf alembic/versions/*
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

#### 5. Port Already in Use

```bash
# Find process using port 3000
# Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :3000
kill -9 <PID>
```

#### 6. Permission Denied (Linux/macOS)

```bash
# Fix permissions
chmod +x .venv/bin/activate
chmod -R 755 src/
```

### Getting Help

1. **Check Documentation:**
   - `docs/01-System-Design.md` - Architecture overview
   - `docs/07-Setup-Installation.md` - This file
   - `README.md` - Quick start

2. **Review Logs:**
   ```bash
   # Application logs
   uv run -m src.api.main 2>&1 | tee app.log
   
   # Docker logs
   docker-compose logs -f app
   ```

3. **Check Environment:**
   ```bash
   # Verify Python version
   python --version  # Should be 3.13+
   
   # Check installed packages
   uv pip list
   
   # Verify .env file
   cat .env
   ```

4. **Create Issue:**
   - Include error message
   - List steps to reproduce
   - Provide environment info (OS, Python version)
   - Attach logs if applicable

## Next Steps

1. **Read the Architecture:**
   - `docs/01-System-Design.md` - ALMS architecture
   - `docs/02-Design-Patterns.md` - Design patterns

2. **Explore the Code:**
   - `src/api/endpoints/v1/` - Sample endpoints
   - `src/execution/` - Business logic
   - `src/agents/` - AI agents

3. **Create Your First Feature:**
   - Add a new endpoint
   - Create a use case
   - Build an AI agent

4. **Run Tests:**
   ```bash
   uv run pytest src/tests -v
   ```

**Updated:** v0.1.0 - Initial setup and installation guide
