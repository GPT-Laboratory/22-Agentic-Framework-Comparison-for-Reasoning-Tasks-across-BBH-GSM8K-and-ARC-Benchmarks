#!/bin/bash
# BabyAGI Framework Setup Script  
# Sets up BabyAGI framework for BBH benchmarking with validation

set -e  # Exit on any error

echo "🤖 Setting up BabyAGI framework..."

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]] || [[ ! -f "main.py" ]]; then
    echo "❌ Error: Must be run from the fm_babyagi directory"
    exit 1
fi

# Read Python version from .python-version file
if [ -f ".python-version" ]; then
    PYTHON_VERSION=$(cat .python-version | tr -d '\n\r')
    echo "📍 Using Python version from .python-version: $PYTHON_VERSION"
else
    echo "❌ .python-version file not found"
    exit 1
fi

# Install dependencies using uv
echo "📦 Installing dependencies..."
if ! uv sync; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed successfully"

# Validate DatasetManager initialization with OpenAI API access
echo "🔑 Validating OpenAI API access..."
if uv run python -c "
import sys
sys.path.append('..')
from utils import DatasetManager
try:
    # This will validate OpenAI API key during initialization
    dataset_mgr = DatasetManager('bbh', 'sample')
    print('✅ DatasetManager initialized with OpenAI API key')
except Exception as e:
    print(f'❌ DatasetManager validation failed: {e}')
    exit(1)
"; then
    echo "✅ OpenAI API key validation successful"
else
    echo "❌ OpenAI API key validation failed"
    exit 1
fi

# Test main.py basic functionality
echo "🧠 Testing BabyAGI main.py functionality..."
if uv run python -c "
import sys
sys.path.append('..')
from main import find_latest_results_file
from utils import DatasetManager

try:
    # Test DatasetManager can be imported and initialized
    dataset_mgr = DatasetManager('bbh', 'sample')
    tasks = dataset_mgr.get_tasks_to_run()
    print(f'✅ BabyAGI integration test successful - {len(tasks)} tasks available')
    print(f'    Tasks: {tasks[:3]}')
    
except Exception as e:
    print(f'❌ BabyAGI integration test failed: {e}')
    exit(1)
"; then
    echo "✅ BabyAGI integration test successful"
else
    echo "❌ BabyAGI integration test failed"
    exit 1
fi

# Create outputs directory
echo "📁 Creating outputs directory..."
mkdir -p outputs
echo "✅ Outputs directory ready"

echo ""
echo "🎉 BabyAGI framework setup complete!"
echo ""
echo "Ready to run:"
echo "  uv run main.py          # Sample mode (first 3 tasks)"
echo "  uv run main.py --full   # Full benchmarking (all 23 tasks)"
echo "  uv run main.py --continue # Continue from latest results"
echo ""