FROM python:3.11-slim

# Install uv from the official image — this is the recommended production pattern
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy lock files first — Docker layer caching means dependency install
# only re-runs when pyproject.toml or uv.lock changes, not on every code change
COPY pyproject.toml uv.lock ./

# --frozen: use uv.lock exactly, fail if it is out of sync with pyproject.toml
# --no-dev: skip dev dependencies (pytest etc.) in production
# --no-cache: do not use the uv cache in the Docker layer (saves image size)
RUN uv sync --frozen --no-dev --no-cache

# Now copy application code (separate layer so code changes don't rebuild deps)
COPY . .

# Generate training data and train the ML model at build time
# This means the scorer is ready on first request without a cold-start delay
RUN uv run python scripts/generate_training_data.py && \
    uv run python ml/train_scorer.py

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]