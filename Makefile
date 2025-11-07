# Makefile for common DevOps MCP workflows: dev, test, build, deploy

# Variables
PYTHON ?= python
PACKAGE := devops_mcps
MOUNT_PATH ?= /mcp
IMAGE_NAME ?= devops-mcps:latest
REGISTRY ?=

# Detect uv (fast Python package manager) if available
UV := $(shell command -v uv 2>/dev/null)
USE_UV := $(if $(UV),yes,no)

.PHONY: help install dev lint format test coverage run run-http build publish docker-build docker-run docker-push clean

help:
	@echo "Available targets:"
	@echo "  install       - Install project and dev dependencies (uv or pip)"
	@echo "  dev           - Install, format, and lint"
	@echo "  lint          - Run ruff checks"
	@echo "  format        - Run ruff formatter"
	@echo "  test          - Run unit tests"
	@echo "  coverage      - Run tests with coverage"
	@echo "  run           - Start MCP server (stdio)"
	@echo "  run-http      - Start MCP server (streamable-http)"
	@echo "  build         - Build sdist and wheel"
	@echo "  publish       - Upload dist/* to PyPI via twine"
	@echo "  docker-build  - Build Docker image ($(IMAGE_NAME))"
	@echo "  docker-run    - Run Docker image locally"
	@echo "  docker-push   - Push Docker image to registry ($(REGISTRY))"
	@echo "  clean         - Remove build and cache artifacts"

install:
ifeq ($(USE_UV),yes)
	@echo "Using uv to sync dependencies..."
	uv sync --all-extras --group dev
else
	@echo "Using pip to install dependencies..."
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e .[dev]
endif

dev: install format lint

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

coverage:
	PYTHONPATH=src $(PYTHON) -m pytest --cov=src/devops_mcps --cov-report=term-missing

run:
	@echo "Starting MCP server (stdio transport)..."
	PYTHONPATH=src $(PYTHON) -m devops_mcps.main_entry

run-http:
	@echo "Starting MCP server (streamable-http) at mount path $(MOUNT_PATH)..."
	PYTHONPATH=src $(PYTHON) -m devops_mcps.main_entry --transport stream_http --mount-path $(MOUNT_PATH)

build:
	@echo "Building sdist and wheel..."
	$(PYTHON) -m pip install -q build
	$(PYTHON) -m build

publish:
	@echo "Publishing to PyPI (requires TWINE_USERNAME/TWINE_PASSWORD or token in ~/.pypirc)..."
	$(PYTHON) -m pip install -q twine
	$(PYTHON) -m twine upload dist/*

docker-build:
	@echo "Building Docker image: $(IMAGE_NAME)"
	docker build -t $(IMAGE_NAME) .

docker-run:
	@echo "Running Docker image: $(IMAGE_NAME)"
	docker run --rm -p 3721:3721 $(IMAGE_NAME)

docker-push:
	@if [ -z "$(REGISTRY)" ]; then echo "REGISTRY is not set. Set REGISTRY and re-run."; exit 1; fi
	@echo "Tagging and pushing Docker image to $(REGISTRY)"
	docker tag $(IMAGE_NAME) $(REGISTRY)/$(IMAGE_NAME)
	docker push $(REGISTRY)/$(IMAGE_NAME)

clean:
	@echo "Cleaning build artifacts and caches..."
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache coverage/html