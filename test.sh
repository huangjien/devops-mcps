#!/bin/bash

# DevOps MCP Server - Test Runner Script
# This script runs unit tests, generates coverage reports, and opens the coverage report

set -e  # Exit on any error

echo "🧪 Starting DevOps MCP Server Test Suite..."
echo "==========================================="

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed. Please install uv first."
    exit 1
fi

# Install dev dependencies if not already installed
echo "📦 Installing dev dependencies..."
uv sync --dev

# Create coverage directory if it doesn't exist
mkdir -p coverage

# Run tests with coverage
echo "🔍 Running unit tests with coverage..."
uv run python -m pytest tests/ \
    --cov=src/devops_mcps \
    --cov-report=html:coverage/html \
    --cov-report=term-missing \
    --cov-report=xml:coverage/coverage.xml \
    --cov-fail-under=80 \
    -v

# Check if tests passed
if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
    echo "📊 Coverage report generated in coverage/html/"
    
    # Open coverage report in default browser
    COVERAGE_FILE="coverage/html/index.html"
    if [ -f "$COVERAGE_FILE" ]; then
        echo "🌐 Opening coverage report..."
        if command -v open &> /dev/null; then
            # macOS
            open "$COVERAGE_FILE"
        elif command -v xdg-open &> /dev/null; then
            # Linux
            xdg-open "$COVERAGE_FILE"
        elif command -v start &> /dev/null; then
            # Windows
            start "$COVERAGE_FILE"
        else
            echo "📁 Please manually open: $COVERAGE_FILE"
        fi
    else
        echo "⚠️  Coverage HTML report not found at $COVERAGE_FILE"
    fi
else
    echo "❌ Tests failed! Check the output above for details."
    exit 1
fi

echo "==========================================="
echo "🎉 Test suite completed successfully!"