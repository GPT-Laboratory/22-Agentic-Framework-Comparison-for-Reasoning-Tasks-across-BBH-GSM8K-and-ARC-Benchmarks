#!/bin/bash

# Google ADK Framework Setup Script
# Sets up Python environment and validates Google API authentication

set -e  # Exit on any error

echo "🔧 Setting up Google ADK framework..."

# Check if .python-version file exists
if [[ ! -f .python-version ]]; then
    echo "❌ Error: .python-version file not found"
    exit 1
fi

PYTHON_VERSION=$(cat .python-version)
echo "📋 Python version: $PYTHON_VERSION"

# Install dependencies using uv
echo "📦 Installing dependencies with uv..."
uv sync

echo "🔐 Validating DatasetManager and ADK setup..."

# Test DatasetManager initialization and ADK setup  
uv run python -c "
import os
import sys

# Import shared utilities
sys.path.append('..')
from utils import DatasetManager

def validate_adk_setup():
    '''Validate DatasetManager initialization and ADK setup'''
    
    # Check DatasetManager can initialize (this validates OpenAI API key)
    try:
        dataset_mgr = DatasetManager('bbh', 'sample')
        print('✅ DatasetManager initialized with OpenAI API key')
    except Exception as e:
        print(f'❌ DatasetManager validation failed: {e}')
        print('   Please ensure OPENAI_API_KEY is set in one of:')
        print('   1. Environment variable: export OPENAI_API_KEY=your_key')
        print('   2. Local .env.local file: OPENAI_API_KEY=your_key')
        print('   3. Project root .env file: OPENAI_API_KEY=your_key')
        print('   Get your key from: https://platform.openai.com/api-keys')
        return False
    
    # Test basic import
    try:
        import google.adk
        print('✅ Google ADK package imported successfully')
    except ImportError as e:
        print(f'❌ Failed to import Google ADK: {e}')
        return False
    
    # Test agent creation with OpenAI model
    try:
        from google.adk.agents import Agent
        from google.adk.models.lite_llm import LiteLlm
        
        # Create LiteLLM model for OpenAI
        model = LiteLlm(model='gpt-4o-mini')
        
        # Create a minimal test agent
        test_agent = Agent(
            name='test_agent',
            model=model,
            instruction='Test agent for validation',
            description='Validation test agent'
        )
        print('✅ Successfully created ADK agent with OpenAI model')
        
        # Note: We don't actually run the agent to avoid API costs during setup
        
    except Exception as e:
        print(f'❌ Failed to create test agent: {e}')
        print('   Please check your OPENAI_API_KEY and internet connection')
        return False
    
    return True

if __name__ == '__main__':
    if not validate_adk_setup():
        sys.exit(1)
    print('🎉 Google ADK setup completed successfully with OpenAI integration!')
"

if [ $? -eq 0 ]; then
    echo "✅ Google ADK framework setup completed successfully!"
    echo "🚀 Ready to run: uv run main.py"
else
    echo "❌ Setup failed. Please check the error messages above."
    exit 1
fi