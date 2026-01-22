#!/bin/bash
set -e  # Exit on any error

echo "🚀 N8N Framework Setup"

# Check directory and install deps
[ ! -f "pyproject.toml" ] && { echo "❌ Run from fm_n8n directory"; exit 1; }
command -v uv >/dev/null || { echo "❌ uv required"; exit 1; }
uv sync

# Start N8N if not running
if ! curl -s http://localhost:5678/healthz >/dev/null 2>&1; then
    command -v docker >/dev/null || { echo "❌ Docker required"; exit 1; }
    docker compose up -d
    echo "⏳ Waiting for N8N..."
    for i in {1..30}; do
        curl -s http://localhost:5678/healthz >/dev/null 2>&1 && break
        [ $i -eq 30 ] && { echo "❌ N8N timeout"; exit 1; }
        sleep 2
    done
fi

# Test existing setup if available
if [ -f ".env.local" ]; then
    source .env.local
    if [ -n "$N8N_WEBHOOK_PATH" ]; then
        echo "🧪 Testing existing setup..."
        http_code=$(curl -s -X POST "http://localhost:5678/webhook/$N8N_WEBHOOK_PATH" \
           -H "Content-Type: application/json" \
           -d '{"prompt":"test","model":"gpt-4.1-nano"}' \
           -w "%{http_code}" -o /dev/null)
        if [ "$http_code" = "200" ]; then
            echo "✅ Existing setup works - ready!"
            echo "Run: uv run main.py"
            exit 0
        fi
        echo "⚠️  Existing setup broken (HTTP $http_code), recreating..."
    fi
fi

# Get API keys
[ -z "$N8N_API_KEY" ] && {
    echo ""
    echo "📋 N8N API Key Setup Required"
    echo "=============================="
    echo "1. 🌐 Open http://localhost:5678 in your browser"
    echo "2. 📧 Enter a VALID EMAIL ADDRESS (required for setup)"
    echo "3. 🔑 Set up your account credentials"
    echo -e "4. 🎫 \033[31mACTIVATE THE FREE LICENSE\033[0m when prompted (\033[31mCRITICAL - API access requires this!\033[0m)"
    echo "5. ⚙️  Go to Settings > n8n API"
    echo "6. 🆕 Click 'Create an API key'"
    echo "7. 📋 Copy the generated key"
    echo ""
    read -p "N8N API Key: " N8N_API_KEY
    [ -z "$N8N_API_KEY" ] && { echo "❌ API key required"; exit 1; }
}

# Validate API key works
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "http://localhost:5678/api/v1/workflows" >/dev/null || {
    echo "❌ Invalid API key"; exit 1; 
}

# Get OpenAI key
[ -z "$OPENAI_API_KEY" ] && {
    [ -f "../../.env" ] && OPENAI_API_KEY=$(grep "^OPENAI_API_KEY=" ../../.env | cut -d'=' -f2 | tr -d '"')
    [ -z "$OPENAI_API_KEY" ] && { echo "❌ OPENAI_API_KEY not found in ../../.env"; exit 1; }
}

# Check workflow template
[ ! -f "workflow_template.json" ] && { echo "❌ workflow_template.json missing"; exit 1; }

# Create credential
echo "📝 Creating resources..."
CRED_RESP=$(curl -s -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" -H "Content-Type: application/json" \
    -d "{\"name\":\"OpenAI BBH $(date +%s)\",\"type\":\"openAiApi\",\"data\":{\"apiKey\":\"$OPENAI_API_KEY\"}}" \
    "http://localhost:5678/api/v1/credentials")

echo "$CRED_RESP" | grep -q '"id"' || { echo "❌ Credential creation failed"; exit 1; }
CREDENTIAL_ID=$(echo "$CRED_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Create workflow
WORKFLOW_JSON=$(sed "s/CREDENTIAL_ID_PLACEHOLDER/$CREDENTIAL_ID/g" workflow_template.json | \
    python3 -c "import sys,json; d=json.load(sys.stdin); d['name']='BBH Agent $(date +%s)'; print(json.dumps(d))")

WORKFLOW_RESP=$(curl -s -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" -H "Content-Type: application/json" \
    -d "$WORKFLOW_JSON" "http://localhost:5678/api/v1/workflows")

echo "$WORKFLOW_RESP" | grep -q '"id"' || { echo "❌ Workflow creation failed"; exit 1; }
WORKFLOW_ID=$(echo "$WORKFLOW_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Activate workflow
curl -s -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
    "http://localhost:5678/api/v1/workflows/$WORKFLOW_ID/activate" >/dev/null

# Extract webhook path
WEBHOOK_PATH=$(python3 -c "
import json
with open('workflow_template.json') as f:
    data = json.load(f)
for node in data['nodes']:
    if node.get('type') == 'n8n-nodes-base.webhook':
        print(node['parameters']['path'])
        break")

# Save config
cat > .env.local << EOF
# N8N Framework Configuration
N8N_URL=http://localhost:5678
N8N_API_KEY=$N8N_API_KEY
N8N_WORKFLOW_ID=$WORKFLOW_ID
N8N_CREDENTIAL_ID=$CREDENTIAL_ID
N8N_WEBHOOK_PATH=$WEBHOOK_PATH
OPENAI_API_KEY=$OPENAI_API_KEY
EOF

# Test setup
echo "🧪 Testing setup..."
test_code=$(curl -s -X POST "http://localhost:5678/webhook/$WEBHOOK_PATH" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"2+2=?","model":"gpt-4.1-nano"}' \
    -w "%{http_code}" -o /dev/null)
[ "$test_code" = "200" ] || { echo "❌ Webhook test failed (HTTP $test_code)"; exit 1; }

echo "✅ Setup complete!"
echo "Run: uv run main.py"
