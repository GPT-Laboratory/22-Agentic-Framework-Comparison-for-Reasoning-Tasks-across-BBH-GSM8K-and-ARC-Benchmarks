#!/bin/bash
set -e  # Exit on any error

echo "🚀 IntentKit Framework Setup"

# Check directory and python version
[ ! -f "pyproject.toml" ] && { echo "❌ Run from fm_intentkit directory"; exit 1; }
[ ! -f ".python-version" ] && { echo "❌ .python-version file missing"; exit 1; }

# Check required tools
command -v uv >/dev/null || { echo "❌ uv required"; exit 1; }
command -v docker >/dev/null || { echo "❌ Docker required"; exit 1; }

# Use .python-version for environment setup
PYTHON_VERSION=$(cat .python-version)
echo "🐍 Setting up Python $PYTHON_VERSION environment"
uv sync

# Check if IntentKit services are already running
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ IntentKit server already running"
else
    echo "🔧 Setting up IntentKit Docker services..."
    
    # Get OpenAI API key first
    if [ -z "$OPENAI_API_KEY" ]; then
        [ -f "../../.env" ] && OPENAI_API_KEY=$(grep "^OPENAI_API_KEY=" ../../.env | cut -d'=' -f2 | tr -d '"')
        [ -z "$OPENAI_API_KEY" ] && { 
            echo "❌ OPENAI_API_KEY not found in ../../.env"
            echo "   Please set OPENAI_API_KEY in the root .env file"
            exit 1
        }
    fi
    
    # Export environment variables for docker-compose
    export OPENAI_API_KEY
    export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
    
    # Start Docker services
    echo "🐳 Starting IntentKit Docker services..."
    docker compose up -d
    
    echo "⏳ Waiting for PostgreSQL to be ready..."
    for i in {1..60}; do
        if docker compose exec postgres pg_isready -U intentkit_user -d intentkit >/dev/null 2>&1; then
            echo "✅ PostgreSQL is ready!"
            break
        fi
        [ $i -eq 60 ] && { 
            echo "❌ PostgreSQL startup timeout"
            docker compose logs postgres
            exit 1
        }
        sleep 2
    done
    
    echo "⏳ Waiting for Redis to be ready..."
    for i in {1..30}; do
        if docker compose exec redis redis-cli ping >/dev/null 2>&1; then
            echo "✅ Redis is ready!"
            break
        fi
        [ $i -eq 30 ] && { 
            echo "❌ Redis startup timeout"
            docker compose logs redis
            exit 1
        }
        sleep 2
    done
    
    echo "⏳ Waiting for IntentKit server to start..."
    for i in {1..90}; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            echo "✅ IntentKit server is ready!"
            break
        fi
        [ $i -eq 90 ] && { 
            echo "❌ IntentKit server startup timeout"
            echo "📋 Docker service status:"
            docker compose ps
            echo "📋 IntentKit server logs:"
            docker compose logs intentkit | tail -20
            exit 1
        }
        sleep 2
    done
fi

# Test existing setup if available
if [ -f ".env.local" ]; then
    source .env.local
    if [ -n "$INTENTKIT_URL" ]; then
        echo "🧪 Testing existing setup..."
        http_code=$(curl -s -X GET "$INTENTKIT_URL/health" \
           -w "%{http_code}" -o /dev/null)
        if [ "$http_code" = "200" ]; then
            echo "✅ Existing setup works - ready!"
            echo "Run: uv run main.py"
            exit 0
        fi
        echo "⚠️  Existing setup broken (HTTP $http_code), recreating..."
    fi
fi

# Create configuration file
echo "📝 Creating configuration..."
cat > .env.local << EOF
# IntentKit Framework Configuration
INTENTKIT_URL=http://localhost:8000
OPENAI_API_KEY=$OPENAI_API_KEY
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}

# Docker service info
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=intentkit_user
POSTGRES_DB=intentkit
REDIS_HOST=localhost
REDIS_PORT=6380
EOF

# Test server health endpoint
echo "🧪 Testing server health..."
http_code=$(curl -s -X GET "http://localhost:8000/health" \
    -w "%{http_code}" -o /dev/null)
[ "$http_code" = "200" ] || { 
    echo "❌ Server health check failed (HTTP $http_code)"
    echo "📋 IntentKit server logs:"
    docker compose logs intentkit | tail -10
    exit 1
}

# Test basic API endpoints
echo "🤖 Testing IntentKit API endpoints..."

# Test if we can access the API
api_response=$(curl -s -X GET "http://localhost:8000/docs" \
    -w "%{http_code}" -o /dev/null 2>/dev/null || echo "404")

if echo "$api_response" | grep -q "200"; then
    echo "✅ IntentKit API documentation accessible"
else
    echo "⚠️  API docs not accessible, but server health OK - proceeding"
fi

# Test agent creation endpoint (if available)
echo "🔍 Discovering available API endpoints..."
endpoints_test=$(curl -s -X GET "http://localhost:8000/" 2>/dev/null || echo "{}")
if echo "$endpoints_test" | grep -q "IntentKit\|agents\|api"; then
    echo "✅ IntentKit API responding with expected content"
else
    echo "⚠️  API content differs from expected - will adapt in main.py"
fi

echo "✅ IntentKit Docker setup complete!"
echo "🐳 Services running:"
echo "  - PostgreSQL: localhost:5433"  
echo "  - Redis: localhost:6380"
echo "  - IntentKit Server: http://localhost:8000"
echo "📋 Configuration saved to .env.local"
echo "📊 Check service status: docker compose ps"
echo "📋 View logs: docker compose logs"
echo "🛑 Stop services: docker compose down"
echo ""
echo "Run: uv run main.py"