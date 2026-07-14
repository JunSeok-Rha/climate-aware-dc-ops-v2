# syntax=docker/dockerfile:1
FROM python:3.14-slim

# Install uv by copying from the official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using frozen lockfile
RUN uv sync --frozen

# Copy source code
COPY src ./src

# Set PYTHONPATH so the cado package is importable
ENV PYTHONPATH=/app/src

# Create non-root user and switch to it
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the application port
EXPOSE 8000

# Run the FastAPI application
CMD ["uv", "run", "uvicorn", "cado.main:app", "--host", "0.0.0.0", "--port", "8000"]
