#!/bin/bash

# TaskWeaver Framework Setup Script
# Sets up Microsoft TaskWeaver for BBH benchmarking

set -e

echo "    Setting up TaskWeaver framework..."

# Check if we're in the correct directory
if [[ ! -f ".python-version" ]]; then
    echo "    ERROR: .python-version not found. Run from fm_taskweaver directory."
    exit 1
fi

# Install core dependencies first
echo "    Installing core dependencies..."
uv sync

# Clone and install TaskWeaver from Git
echo "    Cloning TaskWeaver from GitHub..."
if [[ ! -d "taskweaver_repo" ]]; then
    git clone https://github.com/microsoft/TaskWeaver.git taskweaver_repo
fi

cd taskweaver_repo

# Install TaskWeaver requirements
echo "    Installing TaskWeaver requirements..."
uv add --requirement requirements.txt

cd ..

# Create TaskWeaver project directory structure
echo "    Creating TaskWeaver project structure..."
mkdir -p taskweaver_project/{plugins,logs,workspace,examples/planner_examples,examples/code_generator_examples}

# Generate TaskWeaver configuration file with API key discovery
echo "    Generating TaskWeaver configuration..."
uv run python -c "
import sys
import os
sys.path.append('..')
from utils import DatasetManager
import json

# Discover API key using DatasetManager (this validates and sets the API key)
try:
    dataset_mgr = DatasetManager('bbh', 'sample')
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print('    ERROR: OpenAI API key not found. Please set OPENAI_API_KEY or add to .env file.')
        exit(1)
except Exception as e:
    print(f'    ERROR: Failed to initialize DatasetManager: {e}')
    exit(1)

# Create TaskWeaver configuration
config = {
    'llm.api_base': 'https://api.openai.com/v1',
    'llm.api_key': api_key,
    'llm.model': 'gpt-4o-mini',
    'llm.response_format': 'text',
    'session.max_internal_chat_round_num': 10,
    'logging.level': 'INFO',
    'execution_service.kernel_mode': 'local',
    'code_interpreter.code_verification_on': False,
    'planner.example_base_path': './examples/planner_examples',
    'code_generator.example_base_path': './examples/code_generator_examples',
    'workspace.path': './workspace'
}

# Write configuration file
with open('taskweaver_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print('    ✓ TaskWeaver configuration generated successfully')
"

# Validation: Test import
echo "    Validating TaskWeaver installation..."
uv run python -c "
try:
    import sys
    sys.path.insert(0, 'taskweaver_repo')
    from taskweaver.app.app import TaskWeaverApp
    print('    ✓ TaskWeaver installation successful')
    
    # Test project initialization (without running)
    if not hasattr(TaskWeaverApp, '__init__'):
        raise ImportError('TaskWeaverApp class structure invalid')
    print('    ✓ TaskWeaverApp class accessible')
    
except ImportError as e:
    print(f'    ✗ TaskWeaver import failed: {e}')
    exit(1)
except Exception as e:
    print(f'    ✗ TaskWeaver validation failed: {e}')
    exit(1)
"

if [[ $? -eq 0 ]]; then
    echo "    ✓ TaskWeaver framework setup completed successfully"
    
    # Update setup status in pyproject.toml
    sed -i 's/setup = "notready"/setup = "ready"/' pyproject.toml
    echo "    ✓ Framework marked as ready"
else
    echo "    ✗ TaskWeaver setup failed"
    exit 1
fi