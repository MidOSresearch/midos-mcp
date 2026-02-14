FROM python:3.12-slim

WORKDIR /app

# Install build dependencies for native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition + README (pip needs it for metadata)
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir .

# Copy application code
COPY modules/ modules/
COPY hive_commons/ hive_commons/
COPY .env.example .env

# Data directory for LanceDB
RUN mkdir -p /app/knowledge/memory

EXPOSE 8419

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8419/mcp')" || exit 1

CMD ["python", "-u", "-m", "modules.mcp_server.midos_mcp", "--http", "--host", "0.0.0.0", "--port", "8419"]
