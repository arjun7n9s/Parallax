# Contributing to PARALLAX

## Development Workflow

1. **TDD First**: Write tests before implementation. Every module should have corresponding tests in `tests/`.
2. **Structured Commits**: Use conventional commit messages:
   - `feat:` — new feature
   - `fix:` — bug fix
   - `infra:` — infrastructure change
   - `deps:` — dependency change
   - `ci:` — CI/CD change
   - `docs:` — documentation only
   - `test:` — test additions/fixes
   - `chore:` — maintenance
3. **Pre-commit Hooks**: Run `pre-commit install` to activate linting and secret scanning on every commit.
4. **Code Style**: We use `ruff` for linting and formatting (config in `pyproject.toml`).

## Project Structure

```
parallax/
├── parallax/           # Main Python package
│   ├── api/            # FastAPI routes and endpoints
│   ├── core/           # Config, database, logging, models
│   ├── ai/             # LLM agents, prompts, orchestration (Phase 4)
│   ├── analysis/       # Static + dynamic analysis tools (Phase 2-3)
│   └── workers/        # Celery task workers (Phase 1+)
├── migrations/         # Alembic database migrations
├── scripts/            # Initialization and utility scripts
├── tests/              # Test suite
│   ├── unit/           # Fast, isolated unit tests
│   └── integration/    # Tests requiring backing services
├── rules/              # YARA and Semgrep rule files (Phase 2)
├── docs/               # Architecture and API documentation
└── docker-compose.yml  # Local infrastructure
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Only unit tests (no backing services needed)
pytest tests/unit/ -v

# With coverage
pytest tests/ --cov=parallax --cov-report=term-missing
```
