#!/bin/bash

set -e

echo "Setting up ANUS (Autonomous Networked Utility System) framework..."

# Read Python version from .python-version file
if [ -f ".python-version" ]; then
    PYTHON_VERSION=$(cat .python-version | tr -d '\n\r')
    echo "📍 Using Python version from .python-version: $PYTHON_VERSION"
else
    echo "❌ .python-version file not found"
    exit 1
fi

# Setup Python environment with uv
echo "📦 Setting up Python environment..."
uv sync

echo "🧪 Testing ANUS framework..."
# Test that we can import required modules
if ! uv run python -c "import openai, anthropic, datasets, requests, pydantic, yaml, dotenv, typer, rich; print('✅ All dependencies imported successfully')"; then
    echo "❌ Dependency import test failed"
    exit 1
fi

# Test OpenAI API key availability
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set in environment"
    echo "   Make sure to set it before running: export OPENAI_API_KEY=your_key"
else
    echo "✅ OPENAI_API_KEY found in environment"
fi

echo "✅ ANUS framework setup complete!"
echo "Run: uv run main.py"