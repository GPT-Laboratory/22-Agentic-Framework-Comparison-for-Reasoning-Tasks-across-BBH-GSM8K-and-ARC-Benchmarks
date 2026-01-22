#!/bin/bash

set -e

echo "Setting up OpenAI Agents framework..."

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

# Validate installation
echo "✅ Validating OpenAI Agents installation..."
uv run python -c "
try:
    from agents import Agent, Runner
    print('✅ OpenAI Agents imported successfully')
    
    # Test basic functionality
    agent = Agent(
        name='Test Agent',
        instructions='You are a test agent.'
    )
    print('✅ Agent creation successful')
    
    print('🎉 OpenAI Agents framework setup complete!')
    
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Setup validation failed: {e}')
    exit(1)
"

echo "🚀 OpenAI Agents framework ready for BBH evaluation!"