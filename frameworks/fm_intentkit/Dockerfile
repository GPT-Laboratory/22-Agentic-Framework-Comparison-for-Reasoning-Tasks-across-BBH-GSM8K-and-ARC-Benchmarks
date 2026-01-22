FROM python:3.12.7-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Clone IntentKit repository
RUN git clone https://github.com/crestalnetwork/intentkit.git . && \
    rm -rf .git

# Set up Python environment
RUN uv sync --locked || uv sync

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uv", "run", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]