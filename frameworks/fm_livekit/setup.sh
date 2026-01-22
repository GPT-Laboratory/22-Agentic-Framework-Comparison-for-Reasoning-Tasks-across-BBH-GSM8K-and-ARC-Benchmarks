#!/bin/bash

# LiveKit Agents Framework Setup Script
# Sets up Python 3.13.5 environment and installs LiveKit Agents with OpenAI plugin

set -e  # Exit on any error

echo "🚀 Setting up LiveKit Agents Framework"
echo "======================================"

# Get the Python version from .python-version file  
if [ -f .python-version ]; then
    PYTHON_VERSION=$(cat .python-version)
    echo "📋 Target Python version: $PYTHON_VERSION"
else
    echo "❌ Error: .python-version file not found"
    exit 1
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv package manager not found. Please install uv first."
    exit 1
fi

# Initialize uv project and virtual environment
echo "🔧 Initializing uv project..."
uv venv --python $PYTHON_VERSION
echo "   ✅ Virtual environment created with Python $PYTHON_VERSION"

# Install project dependencies first
echo "📦 Installing base dependencies..."
uv pip install -e .
echo "   ✅ Base dependencies installed"

# Install LiveKit Agents with OpenAI plugin
echo "🤖 Installing LiveKit Agents..."
uv add "livekit-agents[openai]~=1.0"
echo "   ✅ LiveKit Agents with OpenAI plugin installed"

# Sync all dependencies
echo "🔄 Syncing dependencies..."
uv sync
echo "   ✅ Dependencies synchronized"

# Validate installation
echo "🧪 Validating installation..."
if uv run python -c "import livekit.agents; import livekit.plugins.openai; print('LiveKit Agents import successful')"; then
    echo "   ✅ LiveKit Agents validation passed"
else
    echo "   ❌ LiveKit Agents validation failed"
    exit 1
fi

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY environment variable not set"
    echo "   Set it with: export OPENAI_API_KEY=your_api_key"
else
    echo "   ✅ OPENAI_API_KEY found in environment"
fi

echo ""
echo "🎉 LiveKit Agents Framework setup complete!"
echo "📁 Framework: fm_livekit"
echo "🐍 Python: $PYTHON_VERSION"
echo "📦 LiveKit Agents: ~1.0 with OpenAI plugin"
echo ""
echo "Usage:"
echo "  uv run main.py              # Run sample mode (3 tasks)"
echo "  uv run main.py --full       # Run full evaluation (23 tasks)"
echo "  uv run main.py --continue   # Continue from latest results"