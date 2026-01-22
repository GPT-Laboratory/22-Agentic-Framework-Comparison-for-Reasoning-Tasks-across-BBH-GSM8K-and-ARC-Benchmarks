#!/bin/bash

# Letta Framework Setup Script
# Manages Docker server lifecycle and validates full integration

set -e  # Exit immediately if any command fails

echo "🚀 Setting up Letta Framework for BBH Evaluation..."

# Check if running from correct directory
if [[ ! -f ".python-version" ]] || [[ ! -f "pyproject.toml" ]]; then
    echo "❌ Error: Must run setup.sh from fm_letta directory"
    exit 1
fi

# 1. Docker Availability Check
echo "🐳 Checking Docker availability..."
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    echo "   Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Error: Docker daemon is not running"
    echo "   Please start Docker daemon and try again"
    exit 1
fi

echo "✅ Docker is available and running"

# 2. Environment Variable Validation using DatasetManager
echo "🔑 Validating environment variables..."
OPENAI_API_KEY=$(uv run python3 -c "
import sys
import os
sys.path.append('..')
try:
    from utils import DatasetManager
    # This will validate and discover the OpenAI API key
    dataset_mgr = DatasetManager('bbh', 'sample')
    # If successful, get the key from environment (it's now set)
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(api_key)
    else:
        print('', end='')
except Exception as e:
    print('', end='')
")

if [[ -z "${OPENAI_API_KEY}" ]]; then
    echo "❌ Error: OPENAI_API_KEY not found"
    echo "   Please set it via:"
    echo "   - Environment variable: export OPENAI_API_KEY=sk-..."
    echo "   - Local .env.local file: OPENAI_API_KEY=sk-..."
    echo "   - Project .env file: ../../.env"
    exit 1
fi

echo "✅ OPENAI_API_KEY is configured"
export OPENAI_API_KEY

# 3. Python Environment Setup
echo "🐍 Setting up Python environment..."
uv sync

# 4. Add Letta-specific dependencies
echo "📦 Adding Letta framework dependencies..."
uv add letta-client

# 5. Stop any existing Letta containers
echo "🛑 Checking for existing Letta containers..."
if docker ps -a --format 'table {{.Names}}' | grep -q "letta-bbh-server"; then
    echo "🧹 Stopping existing Letta container..."
    docker stop letta-bbh-server || true
    docker rm letta-bbh-server || true
fi

# 6. Start Letta Docker Server
echo "🚀 Starting Letta Docker server..."
docker run -d \
  --name letta-bbh-server \
  -p 8283:8283 \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  letta/letta:latest

# 7. Health Check with Timeout
echo "⏳ Waiting for Letta server to be ready..."
MAX_WAIT=120  # 2 minutes timeout
WAIT_TIME=0
HEALTH_URL="http://localhost:8283"

while [[ $WAIT_TIME -lt $MAX_WAIT ]]; do
    if curl -s --max-time 5 "$HEALTH_URL" > /dev/null 2>&1; then
        echo "✅ Letta server is responding"
        break
    fi
    
    echo "   Waiting for server... (${WAIT_TIME}s/${MAX_WAIT}s)"
    sleep 5
    WAIT_TIME=$((WAIT_TIME + 5))
    
    # Check if container is still running
    if ! docker ps --format 'table {{.Names}}' | grep -q "letta-bbh-server"; then
        echo "❌ Error: Letta container stopped unexpectedly"
        echo "   Container logs:"
        docker logs letta-bbh-server 2>&1 | tail -20
        exit 1
    fi
done

if [[ $WAIT_TIME -ge $MAX_WAIT ]]; then
    echo "❌ Error: Letta server failed to start within ${MAX_WAIT} seconds"
    echo "   Container logs:"
    docker logs letta-bbh-server 2>&1 | tail -20
    exit 1
fi

# 8. Basic Agent Test Cycle
echo "🧪 Running basic agent test cycle..."

# Test agent creation, messaging, and cleanup
uv run python << 'EOF'
import sys
import time
import traceback

try:
    from letta_client import Letta, CreateBlock, MessageCreate
    
    print("   📡 Connecting to Letta server...")
    client = Letta(base_url="http://localhost:8283")
    
    print("   🤖 Creating test agent...")
    test_agent = client.agents.create(
        model="openai/gpt-4.1-nano",
        embedding="openai/text-embedding-3-small",
        memory_blocks=[
            CreateBlock(label="human", value="Test user for BBH validation"),
            CreateBlock(label="persona", value="Test agent for setup validation")
        ]
    )
    
    print(f"   ✅ Agent created with ID: {test_agent.id}")
    
    print("   💬 Testing agent messaging...")
    response = client.agents.messages.create(
        agent_id=test_agent.id,
        messages=[
            MessageCreate(role="user", content="Hello, can you respond with 'Setup test successful'?")
        ]
    )
    
    if response and response.messages:
        print("   ✅ Agent messaging works")
    else:
        print("   ❌ Agent messaging failed")
        sys.exit(1)
    
    print("   🧹 Cleaning up test agent...")
    client.agents.delete(agent_id=test_agent.id)
    print("   ✅ Test agent cleanup successful")
    
    print("✅ All validation tests passed!")
    
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    print("   Please ensure letta-client is installed via uv sync")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Test failed: {e}")
    print("   Traceback:")
    traceback.print_exc()
    sys.exit(1)
EOF

if [[ $? -ne 0 ]]; then
    echo "❌ Basic agent test cycle failed"
    echo "   Container logs:"
    docker logs letta-bbh-server 2>&1 | tail -20
    exit 1
fi

# 9. Update pyproject.toml setup status
echo "📝 Updating setup status to ready..."
if command -v sed &> /dev/null; then
    sed -i 's/setup = "notready"/setup = "ready"/' pyproject.toml
else
    # Fallback for systems without sed
    uv run python -c "
import re
with open('pyproject.toml', 'r') as f:
    content = f.read()
content = re.sub(r'setup = \"notready\"', 'setup = \"ready\"', content)
with open('pyproject.toml', 'w') as f:
    f.write(content)
"
fi

echo ""
echo "🎉 Letta Framework setup completed successfully!"
echo ""
echo "📊 Setup Summary:"
echo "   ✅ Docker server running on port 8283"
echo "   ✅ OpenAI API key configured"
echo "   ✅ Basic agent operations validated"
echo "   ✅ Framework marked as ready"
echo ""
echo "🚀 You can now run: uv run main.py"
echo ""
echo "🛑 To stop the server later: docker stop letta-bbh-server"