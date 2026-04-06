# 👩‍💻 Development Guide

Complete guide for local development and testing.

---

## Quick Start

### 1. Clone & Setup

```bash
# Clone repository
git clone https://github.com/yourusername/biotech-lead-generator.git
cd biotech-lead-generator/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 3. Setup Database

```bash
# Run migrations
alembic upgrade head

# (Optional) Seed test data
python scripts/seed_data.py
```

### 4. Start Development Server

```bash
# Option 1: Direct
uvicorn app.main:app --reload --port 8000

# Option 2: Docker Compose (recommended)
docker-compose up
```

Visit: http://localhost:8000/docs

---

## Running Tests

### All Tests

```bash
# Run complete test suite
pytest

# With coverage report
pytest --cov=app --cov-report=html

# View coverage
open htmlcov/index.html
```

### Specific Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# API tests
pytest tests/api/

# Service tests
pytest tests/services/

# Specific test file
pytest tests/api/test_auth.py

# Specific test function
pytest tests/api/test_auth.py::TestUserRegistration::test_register_valid_user
```

### Watch Mode

```bash
# Auto-run tests on file changes
ptw -- --testmon
```

---

## Code Quality

### Format Code

```bash
# Black (code formatter)
black .

# isort (import sorting)
isort .

# Run both
black . && isort .
```

### Lint Code

```bash
# Flake8
flake8 app/

# Pylint
pylint app/

# MyPy (type checking)
mypy app/
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Database

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

### Database Shell

```bash
# PostgreSQL shell
psql $DATABASE_URL

# Or use Adminer (via Docker)
# Visit: http://localhost:8080
```

---

## Background Jobs

### Start Celery Worker

```bash
# Development
celery -A app.workers.celery_app worker --loglevel=debug

# With autoreload
watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- \
  celery -A app.workers.celery_app worker --loglevel=debug
```

### Start Celery Beat

```bash
celery -A app.workers.celery_app beat --loglevel=info
```

### Monitor with Flower

```bash
celery -A app.workers.celery_app flower

# Visit: http://localhost:5555
```

---

## API Documentation

### Swagger UI

Visit: http://localhost:8000/docs

### ReDoc

Visit: http://localhost:8000/redoc

### Generate OpenAPI Spec

```bash
# Export OpenAPI JSON
curl http://localhost:8000/api/v1/openapi.json > openapi.json
```

---

## Debugging

### VS Code Configuration

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "env": {
        "DEBUG": "True"
      }
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Logging

```python
# In your code
import logging

logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

---

## Performance Profiling

### Profile API Endpoint

```bash
# Install profiler
pip install py-spy

# Profile running process
py-spy top --pid <process_id>

# Record flame graph
py-spy record -o profile.svg -- python -m uvicorn app.main:app
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile function
python -m memory_profiler your_script.py
```

---

## Common Tasks

### Add New Endpoint

1. Create schema in `app/schemas/`
2. Add model in `app/models/`
3. Create service in `app/services/`
4. Add endpoint in `app/api/v1/endpoints/`
5. Write tests in `tests/`

### Add New Background Job

1. Add task in `app/workers/tasks.py`
2. Configure schedule in `app/workers/celery_app.py`
3. Test task execution

### Update Dependencies

```bash
# Update single package
pip install --upgrade package-name

# Update all packages
pip list --outdated
pip install --upgrade -r requirements.txt

# Freeze new requirements
pip freeze > requirements.txt
```

---

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Database Connection Issues

```bash
# Test database connection
python -c "from app.core.database import check_db_connection_sync; print(check_db_connection_sync())"

# Reset database
alembic downgrade base
alembic upgrade head
```

### Import Errors

```bash
# Install package in editable mode
pip install -e .

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

### Redis Connection Issues

```bash
# Test Redis
redis-cli ping

# Check connection
python -c "from app.core.cache import get_sync_redis; print(get_sync_redis().ping())"
```

---

## Best Practices

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings
- Keep functions small
- Use meaningful variable names

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new search filter
fix: resolve database connection issue
docs: update API documentation
test: add tests for authentication
refactor: improve lead scoring algorithm
chore: update dependencies
```

---

## Resources

- 📚 [FastAPI Docs](https://fastapi.tiangolo.com)
- 📚 [SQLAlchemy Docs](https://docs.sqlalchemy.org)
- 📚 [Celery Docs](https://docs.celeryproject.org)
- 📚 [Pytest Docs](https://docs.pytest.org)

---

**Happy Coding! 🚀**