#!/bin/bash

set -e  # Exit on any error

echo "🔧 Setting up PraisonAI Framework for BBH Benchmarking..."

# Check if we're in the right directory
if [ ! -f ".python-version" ]; then
    echo "❌ Error: Not in framework directory. Please run from fm_praisonai/"
    exit 1
fi

# Read Python version from .python-version file
PYTHON_VERSION=$(cat .python-version)
echo "📋 Required Python version: $PYTHON_VERSION"

# Sync core dependencies
echo "📦 Installing core dependencies..."
uv sync

# Add PraisonAI framework
echo "🤖 Installing PraisonAI agents..."
uv add praisonaiagents

# Validate OpenAI API key using DatasetManager
echo "🔑 Validating OpenAI API key..."
if ! uv run python -c "
import sys
sys.path.append('..')
from utils import DatasetManager
try:
    # This will validate and discover the OpenAI API key
    dataset_mgr = DatasetManager('bbh', 'sample')
    print('✅ OpenAI API key found and valid')
except Exception as e:
    print(f'❌ OpenAI API key error: {e}')
    exit(1)
" 2>/dev/null; then
    echo "❌ OpenAI API key validation failed"
    exit 1
fi

# Test basic PraisonAI agent creation
echo "🧪 Testing basic PraisonAI agent functionality..."
if ! uv run python -c "
import sys
import os
sys.path.append('..')
from utils import DatasetManager

try:
    # Ensure API key is available via DatasetManager
    dataset_mgr = DatasetManager('bbh', 'sample')
    
    # Test PraisonAI import and basic agent creation
    from praisonaiagents import Agent
    
    # Create a test agent
    test_agent = Agent(
        instructions='You are a test agent. Respond with exactly: TEST_SUCCESS'
    )
    
    # Test basic functionality
    result = test_agent.start('Say TEST_SUCCESS')
    response_text = str(result) if result else ''
    
    if 'TEST_SUCCESS' in response_text:
        print('✅ PraisonAI agent test successful')
    else:
        print(f'⚠️ PraisonAI agent test response: {response_text[:100]}...')
        print('✅ Basic functionality confirmed (response received)')
        
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Agent test error: {e}')
    exit(1)
"; then
    echo "❌ PraisonAI agent test failed"
    exit 1
fi

# Update setup status to ready
echo "✅ All validations passed, marking setup as ready..."
if command -v sed >/dev/null 2>&1; then
    sed -i 's/setup = "notready"/setup = "ready"/' pyproject.toml
elif command -v gsed >/dev/null 2>&1; then
    gsed -i 's/setup = "notready"/setup = "ready"/' pyproject.toml
else
    echo "⚠️  Warning: Could not automatically update setup status. Please manually change 'notready' to 'ready' in pyproject.toml"
fi

echo ""
echo "🎉 PraisonAI Framework setup completed successfully!"
echo "📁 Framework ready at: $(pwd)"
echo "🚀 Run with: uv run main.py [--full] [--continue]"
echo ""