# DevOps MCP Server

A FastMCP-based MCP server providing DevOps tools and integrations.

## Features

- GitHub repository search and management
- File content retrieval from repositories
- Issue tracking and management
- Code search functionality

## Installation

To install the package, use the following command:

```bash
pip install devops-mcps
```

## Usage

Run the MCP server:
```bash
devops-mcps
```

## Configuration

### Environment Variables

Set the required environment variable for GitHub API access:


```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
```

### JSON Configuration
Create a `config.json` file:
```json
{
  "github": {
    "access_token": "your_token_here",
    "api_url": "https://api.github.com"
  },
  "server": {
    "port": 8000,
    "debug": false
  }
}
```

## UVX Configuration

Install UVX tools:
```bash
uvx install
```

Run with UVX:
```bash
uvx run devops-mcps
```

## Transport Configuration

The MCP server supports two transport types:
- `stdio` (default): Standard input/output communication
- `sse`: Server-Sent Events for HTTP-based communication

### Local Usage
```bash
# Default stdio transport
devops-mcps

# SSE transport
devops-mcps --transport sse
```

### UVX Usage
```bash
# Default stdio transport
uvx run devops-mcps

# SSE transport
uvx run devops-mcps-sse
```

## Docker Configuration

Build the Docker image:
```bash
docker build -t devops-mcps .
```

Run the container:
```bash
docker run -p 8000:8000 devops-mcps
```

## VSCode Configuration

To use this MCP server in vs code copilot, there are 2 ways to configure it in VSCode settings.json with different transport types:

### UVX Configuration

#### stdio Transport (default)
```json
"devops-mcps": {
  "type": "stdio",
  "command": "uvx",
  "args": ["devops-mcps"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxCe"
  }
}
```

#### SSE Transport
```json
"devops-mcps": {
  "type": "sse",
  "command": "uvx",
  "args": ["devops-mcps-sse"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxCe"
  }
}
```

### Docker Configuration

#### stdio Transport (default)
```json
"devops-mcps": {
  "command": "docker",
  "args": [
    "run",
    "-i",
    "huangjien/devops-mcps:latest"
  ],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxx2Ce"
  }
}
```

#### SSE Transport (MCP Server Deployed in Remote Docker Container)
```json
"devops-mcps": {
  "type": "sse",
  "url": "http://[remote ip address]:8000/sse",
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxx2Ce"
  }
}
```

## Development

Install development dependencies:
```bash
pip install -e .[dev]
```

Run mcp inspector to test or debug:

```bash
npx @modelcontextprotocol/inspector uv run devops-mcps
```

## CI/CD Pipeline

GitHub Actions workflow will automatically:
1. Build and publish Python package to PyPI
2. Build and push Docker image to Docker Hub

### Required Secrets
Set these secrets in your GitHub repository:
- `PYPI_API_TOKEN`: Your PyPI API token
- `DOCKER_HUB_USERNAME`: Your Docker Hub username
- `DOCKER_HUB_TOKEN`: Your Docker Hub access token

Workflow triggers on push to `main` branch.
## Packaging and Publishing

### Install tools

```bash
pip install -U twine build  
```

### Build the package
```bash
python -m build
```

### Upload to PyPI
1. Create a `~/.pypirc` file with your API token:
```ini
[pypi]
username = __token__
password = your_pypi_api_token_here
```

2. Upload the package:
```bash
twine upload dist/*
```

### Important Notes
- Ensure all classifiers in `pyproject.toml` are valid PyPI classifiers
- Remove deprecated license classifiers in favor of SPDX license expressions
- The package will be available at: https://pypi.org/project/devops-mcps/
- Update the version everytime, or when you push, it will show an error: already exists.


## License

MIT