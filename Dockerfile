# Multi-stage Docker image for option-finder scanner
# Optimized for GitHub Actions CI/CD with insider trading enrichment

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies (minimal footprint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Install finviz-mcp for insider enrichment
RUN pip install --no-cache-dir --user \
    -e git+https://github.com/xrichini/finviz-mcp.git@master#egg=finviz-mcp

# Stage 2: Runtime (minimal image)
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY scan_daemon.py .
COPY api ./api
COPY services ./services
COPY data ./data
COPY db ./db
COPY models ./models

# Ensure pip packages are in PATH
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

# Default command
CMD ["python", "scan_daemon.py", "--once", "--force"]
