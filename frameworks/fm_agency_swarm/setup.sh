#!/bin/bash

# Agency-swarm Framework Setup Script
# Installs dependencies and validates the framework integration

set -e  # Exit on any error

echo "🤖 Setting up Agency-swarm Framework Integration"
echo "=" * 50

# Check if .python-version exists and get Python version
if [ -f ".python-version" ]; then
    PYTHON_VERSION=$(cat .python-version)
    echo "📋 Target Python version: $PYTHON_VERSION"
else
    echo "❌ .python-version file not found"
    exit 1
fi

# Install basic dependencies first
echo "📦 Installing core BBH dependencies..."
uv sync

# Install agency-swarm - this is the main framework dependency
echo "📦 Installing agency-swarm framework..."
uv add "agency-swarm>=0.2.0"

# Validate installation by trying to import
echo "✅ Validating installation..."
uv run python -c "
import sys
print(f'Python version: {sys.version}')

try:
    from agency_swarm import Agent, Agency
    print('✅ Agency-swarm import successful')
    
    # Test basic agent creation
    test_agent = Agent(
        name='TestAgent',
        description='Test agent for validation',
        instructions='You are a test agent.',
        model='gpt-4o-mini'
    )
    print('✅ Agent creation successful')
    
    # Test agency creation  
    test_agency = Agency([test_agent])
    print('✅ Agency creation successful')
    
    print('✅ All validations passed')
    
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Validation error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Setup completed successfully!"
    echo "🎯 Framework ready for BBH evaluation"
    
    # Update setup status in pyproject.toml
    if [ -f "pyproject.toml" ]; then
        sed -i 's/setup = "notready"/setup = "ready"/' pyproject.toml
        echo "📝 Updated setup status to 'ready'"
    fi
    
    echo ""
    echo "🚀 Usage:"
    echo "  uv run main.py              # Run sample mode (first 3 tasks)"
    echo "  uv run main.py --full       # Run all 23 BBH tasks"
    echo "  uv run main.py --continue   # Continue from latest results"
else
    echo "❌ Setup failed!"
    exit 1
fi