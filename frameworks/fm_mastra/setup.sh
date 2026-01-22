#!/bin/bash

# Mastra Framework Setup Script for BBH Evaluation
# Sets up both Node.js dependencies and Python environment

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Mastra framework for BBH evaluation...${NC}"
echo "=" * 60

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get the required Python version
get_python_version() {
    if [ -f .python-version ]; then
        cat .python-version
    else
        echo "3.13.5"
    fi
}

# 1. Check and install Node.js if needed
echo -e "${YELLOW}[1/6] Checking Node.js installation...${NC}"

if ! command_exists node; then
    echo -e "${RED}Node.js is not installed. Please install Node.js 18+ from https://nodejs.org/${NC}"
    exit 1
fi

NODE_VERSION=$(node --version | sed 's/v//')
NODE_MAJOR=$(echo $NODE_VERSION | cut -d. -f1)

if [ "$NODE_MAJOR" -lt 18 ]; then
    echo -e "${RED}Node.js version $NODE_VERSION is too old. Please install Node.js 18 or later.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Node.js ${NODE_VERSION} is installed${NC}"

# 2. Check npm
if ! command_exists npm; then
    echo -e "${RED}npm is not installed. Please install npm.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ npm $(npm --version) is installed${NC}"

# 3. Install Node.js dependencies
echo -e "\n${YELLOW}[2/6] Installing Node.js dependencies...${NC}"

if [ -f package.json ]; then
    npm install
    echo -e "${GREEN}✓ Node.js dependencies installed${NC}"
else
    echo -e "${RED}package.json not found${NC}"
    exit 1
fi

# 4. Check Python and uv installation
echo -e "\n${YELLOW}[3/6] Checking Python environment...${NC}"

REQUIRED_PYTHON_VERSION=$(get_python_version)
echo "Required Python version: $REQUIRED_PYTHON_VERSION"

if ! command_exists uv; then
    echo -e "${RED}uv is not installed. Please install uv from https://docs.astral.sh/uv/${NC}"
    exit 1
fi

echo -e "${GREEN}✓ uv $(uv --version | cut -d' ' -f2) is installed${NC}"

# 5. Install Python dependencies
echo -e "\n${YELLOW}[4/6] Installing Python dependencies...${NC}"

# uv will automatically install the correct Python version from .python-version
uv sync --frozen

echo -e "${GREEN}✓ Python dependencies installed${NC}"

# 6. Verify OpenAI API key
echo -e "\n${YELLOW}[5/6] Checking OpenAI API key...${NC}"

if [ -z "$OPENAI_API_KEY" ] && [ ! -f .env.local ] && [ ! -f ../../.env ]; then
    echo -e "${YELLOW}⚠ OpenAI API key not found in environment variables.${NC}"
    echo "Make sure to set OPENAI_API_KEY before running the evaluation."
    echo "You can:"
    echo "  1. Set environment variable: export OPENAI_API_KEY=your_key"
    echo "  2. Create .env.local file: echo 'OPENAI_API_KEY=your_key' > .env.local"
    echo "  3. Use project root .env file: echo 'OPENAI_API_KEY=your_key' >> ../../.env"
else
    echo -e "${GREEN}✓ OpenAI API key configuration found${NC}"
fi

# 7. Validate installation
echo -e "\n${YELLOW}[6/6] Validating installation...${NC}"

# Test Node.js Mastra installation
if node -e "import('@mastra/core/agent').then(() => console.log('Mastra core loaded')).catch(e => process.exit(1))"; then
    echo -e "${GREEN}✓ Mastra core library accessible${NC}"
else
    echo -e "${RED}✗ Mastra core library validation failed${NC}"
    exit 1
fi

# Test OpenAI SDK
if node -e "import('@ai-sdk/openai').then(() => console.log('OpenAI SDK loaded')).catch(e => process.exit(1))"; then
    echo -e "${GREEN}✓ OpenAI SDK accessible${NC}"
else
    echo -e "${RED}✗ OpenAI SDK validation failed${NC}"
    exit 1
fi

# Test Python dependencies
echo "Testing Python dependencies..."
uv run python -c "
import sys
import requests
import datasets  
import json
sys.path.append('..')
from utils import DatasetManager
# Test DatasetManager initialization
dataset_mgr = DatasetManager('bbh', 'sample')
tasks = dataset_mgr.get_tasks_to_run()
print('All Python dependencies available')
print(f'Available BBH tasks: {len(tasks)}')
print(f'DatasetManager initialized successfully')
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Python environment validation passed${NC}"
else
    echo -e "${RED}✗ Python environment validation failed${NC}"
    exit 1
fi

# Success message
echo -e "\n${GREEN}Setup completed successfully!${NC}"
echo "=" * 60
echo "Quick start:"
echo "  • Sample run (3 tasks): uv run main.py"
echo "  • Full run (all tasks):  uv run main.py --full"
echo "  • Custom model:         BBH_MODEL=gpt-4o-mini uv run main.py"
echo ""
echo "The system will automatically:"
echo "  1. Start a Mastra agent server on an available port (3000-3099)"
echo "  2. Process BBH questions through the agent"
echo "  3. Save results to outputs/mastra_bbh_*.json"
echo "  4. Clean up the server when done"
echo ""
echo -e "${YELLOW}Note: First run may take longer as Node.js loads the Mastra framework${NC}"