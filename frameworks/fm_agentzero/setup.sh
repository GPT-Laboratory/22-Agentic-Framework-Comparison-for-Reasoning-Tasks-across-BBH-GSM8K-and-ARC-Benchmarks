#!/bin/bash
set -e

echo "🤖 Setting up AgentZero framework..."

echo "📦 Installing client dependencies..."
if ! uv sync; then
    echo "❌ ERROR: Failed to install dependencies"
    exit 1
fi
echo "✅ Client dependencies installed"

echo "🔑 Validating OpenAI API access (used by utils.py for answer extraction)..."
if ! uv run python -c "
import sys
sys.path.append('..')
from utils import DatasetManager
try:
    dataset_mgr = DatasetManager('bbh', 'sample')
    print('✅ DatasetManager initialized with OpenAI API key')
except Exception as e:
    print(f'❌ DatasetManager validation failed: {e}')
    exit(1)
"; then
    echo "❌ ERROR: OpenAI API key validation failed"
    exit 1
fi

echo "🌐 Checking whether Agent Zero is reachable..."
BASE_URL="${AGENTZERO_BASE_URL:-http://localhost:50080/api}"
if [ -z "$AGENTZERO_API_KEY" ]; then
    echo "⚠️  AGENTZERO_API_KEY is not set - skipping live connectivity check."
else
    if uv run python -c "
import os, requests, sys
base = os.environ.get('AGENTZERO_BASE_URL', 'http://localhost:50080/api')
key = os.environ.get('AGENTZERO_API_KEY')
try:
    r = requests.post(f'{base}/api_message', headers={'X-API-KEY': key, 'Content-Type': 'application/json'}, json={'message': 'Reply with just: ready'}, timeout=120)
    r.raise_for_status()
    data = r.json()
    if 'error' in data:
        print(f'❌ Agent Zero responded with an error: {data[\"error\"]}')
        sys.exit(1)
    print('✅ Agent Zero is reachable and responded:', data.get('response'))
except Exception as e:
    print(f'❌ Could not reach Agent Zero: {e}')
    sys.exit(1)
"; then
        echo "✅ Agent Zero connectivity confirmed"
    else
        echo "❌ ERROR: Could not reach Agent Zero - is the container running? (docker ps)"
        exit 1
    fi
fi

echo "📁 Creating outputs directory..."
mkdir -p outputs
echo "✅ Outputs directory ready"

echo ""
echo "🎉 AgentZero client setup complete!"
echo ""
echo "Ready to run:"
echo "  uv run main.py          # Sample mode"
echo "  uv run main.py --full   # Full benchmarking"
echo "  uv run main.py --continue"
