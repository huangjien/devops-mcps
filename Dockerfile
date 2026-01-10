# DevOps MCP Server - Multi-stage Dockerfile
# Stage 1: Builder stage
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Copy dependency files and source code
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Install dependencies
RUN uv pip install --system --no-cache-dir .

# Stage 2: Runtime stage
FROM python:3.12-slim

# Set environment variables for MCP server configuration
ARG GITHUB_PERSONAL_ACCESS_TOKEN
ARG GITHUB_API_URL
ARG JENKINS_URL
ARG JENKINS_USER
ARG JENKINS_TOKEN
ARG ARTIFACTORY_URL
ARG ARTIFACTORY_IDENTITY_TOKEN
ARG ARTIFACTORY_USERNAME
ARG ARTIFACTORY_PASSWORD
ARG LOG_LENGTH
ARG MCP_PORT

# Create non-root user for security
RUN groupadd -r devops && useradd -r -g devops devops

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=devops:devops . .

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Expose the port for stream_http transport (matching documentation)
EXPOSE 3721

# Set environment variable for transport type
ENV TRANSPORT_TYPE=stdio

# Switch to non-root user
USER devops

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Command to run the MCP server using uv with transport type selection
ENTRYPOINT ["/bin/sh", "-c", "if [ \"$TRANSPORT_TYPE\" = \"stream_http\" ]; then python -m devops_mcps.main_entry --transport stream_http; else python -m devops_mcps.main_entry; fi"]
