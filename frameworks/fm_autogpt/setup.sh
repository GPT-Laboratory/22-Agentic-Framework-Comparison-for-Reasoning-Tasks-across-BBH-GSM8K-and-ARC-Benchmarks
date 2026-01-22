#!/bin/bash

set -e

echo "Setting up AutoGPT framework..."

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

# Verify AutoGPT-Forge installation
echo "🔍 Verifying AutoGPT-Forge installation..."
if uv run python -c "from forge.sdk import Agent, AgentDB, Workspace; from forge.llm import chat_completion_request; print('✅ AutoGPT-Forge SDK verified')" 2>/dev/null; then
    echo "✅ AutoGPT-Forge installation successful"
    # Update setup status to ready
    sed -i 's/setup = "notready"/setup = "ready"/' pyproject.toml
    echo "✅ AutoGPT setup complete!"
else
    echo "❌ AutoGPT-Forge verification failed"
    echo "❌ Setup failed - AutoGPT components not available"
    exit 1
fi