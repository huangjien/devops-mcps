#!/usr/bin/env bash

# DevOps MCP Server - Test Runner Script
# This script runs unit tests, generates coverage reports, and opens the coverage report

set -euo pipefail

echo "🧪 Starting DevOps MCP Server Test Suite..."
echo "==========================================="

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed. Please install uv first."
    exit 1
fi

echo "📦 Installing dev dependencies..."
uv sync --all-extras --group dev

# Create coverage directory if it doesn't exist
mkdir -p coverage

# Run tests with coverage
echo "🔍 Running unit tests with coverage..."
if uv run python -m pytest tests/ \
  --cov=src/devops_mcps \
  --cov-report=html:coverage/html \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-fail-under=80 \
  -v; then
    echo "✅ All tests passed!"
    echo "📊 Coverage report generated in coverage/html/"
    
    COVERAGE_FILE="coverage/html/index.html"
    if [ -z "${CI:-}" ] && [ -f "$COVERAGE_FILE" ]; then
        echo "🌐 Opening coverage report..."
        if command -v open &> /dev/null; then
            open "$COVERAGE_FILE"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$COVERAGE_FILE"
        elif command -v start &> /dev/null; then
            start "$COVERAGE_FILE"
        else
            echo "📁 Please manually open: $COVERAGE_FILE"
        fi
    elif [ -f "$COVERAGE_FILE" ]; then
        echo "📁 Coverage report: $COVERAGE_FILE"
    else
        echo "⚠️  Coverage HTML report not found at $COVERAGE_FILE"
    fi
else
    echo "❌ Tests failed! Check the output above for details."
    exit 1
fi

echo "==========================================="
echo "🎉 Test suite completed successfully!"
