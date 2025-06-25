ARG GITHUB_PERSONAL_ACCESS_TOKEN

# Stage 1: Build stage
FROM python:3.13-slim

# Install curl and gnupg for Node.js installation
RUN apt-get update && apt-get install -y curl gnupg

# Install Node.js and npm
# RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
#     && apt-get install -y nodejs

RUN python3 -m venv /app/.venv
# Install pip and uv into the virtual environment
RUN /app/.venv/bin/python3 -m pip install --upgrade pip uv


WORKDIR /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
COPY . .
RUN python3 -m pip install .
# Expose the port your MCP server will run on
EXPOSE 8000

# Environment variable for transport type
ENV TRANSPORT_TYPE=stdio

# Command to run the MCP server using uv with transport type selection
ENTRYPOINT ["/bin/sh", "-c", "if [ \"$TRANSPORT_TYPE\" = \"stream_http\" ]; then /app/.venv/bin/uv run devops-mcps-stream-http; else /app/.venv/bin/uv run devops-mcps; fi"]

