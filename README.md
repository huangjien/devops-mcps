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

### UVX Way
1. Install the UVX extension in VSCode
2. Create a `.vscode/settings.json` file:
```json
{
  "uvx.command": "devops-mcps",
  "uvx.port": 8000
}
```
3. Press F5 to start debugging

### Docker Way

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
1. Reopen in Container

## Development

Install development dependencies:
```bash
pip install -e .[dev]
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