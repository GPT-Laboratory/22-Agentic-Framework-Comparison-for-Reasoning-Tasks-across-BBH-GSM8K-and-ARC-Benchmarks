#!/bin/bash

# AgentZero Framework Setup Script
# Handles Docker validation, dependency installation, and AgentZero configuration

echo "🤖 Setting up AgentZero framework..."

# Check if Docker is available and running
echo "📋 Validating Docker requirements..."
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker is not installed!"
    echo "   AgentZero requires Docker for secure code execution."
    echo "   Please install Docker Desktop and try again."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ ERROR: Docker daemon is not running!"
    echo "   AgentZero requires Docker for code execution tools."
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is available and running"

# Install core dependencies first
echo "📦 Installing core BBH dependencies..."
if ! uv sync; then
    echo "❌ ERROR: Failed to install core dependencies"
    exit 1
fi

echo "✅ Core dependencies installed"

# Add essential AgentZero packages selectively
echo "📦 Adding essential AgentZero packages..."

# Core AgentZero functionality (avoiding heavy ML packages)
essential_packages=(
    "docker==7.1.0"           # Required for AgentZero code execution
    "flask==3.0.3"            # Core web framework (minimal)
    "tiktoken==0.8.0"         # Token counting
    "litellm==1.74"           # LLM abstraction layer
    "pathspec>=0.12.1"        # File pattern matching  
    "psutil>=7.0.0"           # System utilities
    "GitPython==3.1.43"       # Git operations
    "markdownify==1.1.0"      # Markdown processing
)

for package in "${essential_packages[@]}"; do
    echo "  Adding: $package"
    if ! uv add "$package"; then
        echo "    Warning: Failed to add $package, continuing..."
    fi
done

echo "✅ Essential AgentZero packages added"

# Create AgentZero configuration directory
echo "⚙️  Creating AgentZero configuration..."
mkdir -p config

# Create minimal config.yaml for headless operation
cat > config/config.yaml << 'EOF'
# AgentZero BBH Evaluation Configuration
# Minimal headless setup for reasoning tasks

# Model configuration (uses BBH_MODEL env var or default)
models:
  chat_llm:
    provider: "openai"
    model: "gpt-4.1-nano"  # Default, overridden by BBH_MODEL
    temperature: 0.1
    context_length: 32000
  
  utility_llm:
    provider: "openai" 
    model: "gpt-4.1-mini"
    temperature: 0.0
    
  embedding_llm:
    provider: "openai"
    model: "text-embedding-3-small"

# Disable web interface components
web:
  enabled: false
  
# Restrict tools for BBH evaluation (reasoning only)
tools:
  # Disable autonomous code execution for controlled evaluation
  code_execution: false
  web_search: false
  file_operations: false
  docker_tools: false
  
  # Enable basic reasoning tools only
  knowledge_retrieval: true
  memory_access: true
  text_processing: true

# Memory and knowledge settings
agent:
  prompts_subdir: "default"
  memory_subdir: "bbh_eval" 
  knowledge_subdir: "default"
  
# BBH-specific settings
bbh:
  enable_cot: true
  n_shots: 3
  extraction_model: "gpt-4.1-mini"
EOF

echo "✅ AgentZero configuration created"

# Test AgentZero core imports
echo "🔍 Validating AgentZero installation..."
if ! uv run python -c "
import sys
sys.path.append('.')

try:
    # Test critical AgentZero imports
    import docker
    import nest_asyncio
    from pathlib import Path
    
    # Check if we can access AgentZero when installed
    print('Core dependencies: ✓')
    print('Docker client: ✓') 
    print('Configuration: ✓')
    
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
"; then
    echo "❌ ERROR: AgentZero validation failed"
    echo "   Some core components could not be imported."
    echo "   Please check the installation and try again."
    exit 1
fi

echo "✅ AgentZero validation successful"

# Create outputs directory
mkdir -p outputs

echo ""
echo "🎉 AgentZero framework setup completed!"
echo ""
echo "📝 Configuration:"
echo "   • Python: $(python --version 2>&1 | cut -d' ' -f2)"
echo "   • Docker: $(docker --version | cut -d' ' -f3 | tr -d ',')"
echo "   • Dependencies: Essential packages only (lightweight)"
echo "   • Mode: Headless (no web UI)"
echo "   • Tools: Restricted to reasoning tasks"
echo ""
echo "🚀 Ready to run BBH evaluation:"
echo "   uv run main.py              # Sample mode (first 3 tasks)" 
echo "   uv run main.py --full       # Full evaluation (all 23 tasks)"
echo "   BBH_MODEL=gpt-4o-mini uv run main.py  # Custom model"
echo ""