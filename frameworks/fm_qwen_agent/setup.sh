#!/bin/bash
set -e  # Exit on any error

echo "🚀 Qwen-Agent Framework Setup"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from fm_qwen_agent directory"
    exit 1
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv package manager is required"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Read Python version from .python-version
if [ -f ".python-version" ]; then
    PYTHON_VERSION=$(cat .python-version)
    echo "📋 Using Python version: $PYTHON_VERSION"
else
    echo "❌ Error: .python-version file not found"
    exit 1
fi

# Setup Python environment and install dependencies
echo "📦 Installing dependencies with uv..."
uv sync

# Test basic import functionality
echo "🧪 Testing Qwen-Agent import..."
if uv run python -c "from qwen_agent.agents import Assistant; print('✅ Qwen-Agent import successful')" 2>/dev/null; then
    echo "✅ Qwen-Agent integration validated"
else
    echo "❌ Error: Qwen-Agent import failed"
    exit 1
fi

echo "✅ Qwen-Agent framework setup complete!"
echo ""
echo "🚀 Ready to run:"
echo "  uv run main.py                    # Run first 3 tasks (sample mode)"
echo "  uv run main.py --full            # Run all 23 BBH tasks"
echo "  uv run main.py --continue        # Continue interrupted evaluation"