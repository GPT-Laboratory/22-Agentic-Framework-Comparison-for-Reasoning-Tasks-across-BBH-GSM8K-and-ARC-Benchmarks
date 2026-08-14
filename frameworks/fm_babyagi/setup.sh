#!/bin/bash
set -e

echo "🤖 Setting up BabyAGI (pip package, https://github.com/yoheinakajima/babyagi) framework..."

echo "📦 Installing dependencies (includes the real 'babyagi' pip package)..."
if ! uv sync; then
    echo "❌ ERROR: Failed to install dependencies"
    exit 1
fi
echo "✅ Dependencies installed"

echo "🔑 Validating OpenAI API access..."
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

echo "🔧 Patching babyagi's bundled react_agent.py..."
echo "   (Original hardcodes model=gpt-4-turbo, temperature=0.7, max_tokens=1500"
echo "   with no way to override them - patched here to use BABYAGI_MODEL/gpt-5.2,"
echo "   temperature=0, max_tokens=1200 (or max_completion_tokens for gpt-5.x/o1/o3/o4)."
echo "   Idempotent - safe to re-run any time, e.g. after a package upgrade.)"

REACT_AGENT_PATH=$(uv run python -c "import babyagi, os; print(os.path.join(os.path.dirname(babyagi.__file__), 'functionz', 'packs', 'drafts', 'react_agent.py'))" 2>/dev/null | tail -1)

if [ -z "$REACT_AGENT_PATH" ] || [ ! -f "$REACT_AGENT_PATH" ]; then
    echo "❌ ERROR: Could not locate react_agent.py in the installed babyagi package"
    exit 1
fi

uv run python - "$REACT_AGENT_PATH" <<'PYEOF'
import sys

path = sys.argv[1]
with open(path) as f:
    content = f.read()

if "BABYAGI_REACT_AGENT_MODEL" in content:
    print("✅ Already patched, nothing to do")
else:
    old = """            response = litellm.completion(
                model="gpt-4-turbo",
                messages=chat_context,
                tools=tools,
                tool_choice="auto",
                max_tokens=1500,
                temperature=0.7
            )"""

    new = """            import os as _os
            _model = _os.getenv("BABYAGI_REACT_AGENT_MODEL", "gpt-5.2")
            _token_param = "max_completion_tokens" if _model.startswith(("gpt-5", "o1", "o3", "o4")) else "max_tokens"
            _completion_kwargs = {
                "model": _model,
                "messages": chat_context,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0,
                _token_param: 1200,
            }
            response = litellm.completion(**_completion_kwargs)"""

    if old in content:
        content = content.replace(old, new)
        with open(path, "w") as f:
            f.write(content)
        print("✅ Patched successfully")
    else:
        print("❌ Expected block not found - the installed package version may differ from what this patch expects.")
        print("   Manual fix needed: open the file above and hardcode model/temperature/max_tokens as needed.")
        sys.exit(1)
PYEOF

echo "🔍 Verifying react_agent registers correctly..."
if ! uv run python -c "
import babyagi
babyagi.load_functions('drafts/react_agent')
assert callable(babyagi.react_agent)
print('✅ react_agent loaded and callable')
" 2>&1 | tail -5; then
    echo "❌ ERROR: react_agent failed to load/register"
    exit 1
fi

echo "📁 Creating outputs directory..."
mkdir -p outputs
echo "✅ Outputs directory ready"

echo ""
echo "🎉 BabyAGI (pip package) setup complete!"
echo ""
echo "Ready to run:"
echo "  uv run main.py          # Sample mode"
echo "  uv run main.py --full   # Full benchmarking"
echo "  uv run main.py --continue"
echo ""
echo "Optional: set BABYAGI_DASHBOARD=1 to also launch the real dashboard at"
echo "http://localhost:8080/dashboard alongside the benchmark run, e.g.:"
echo "  BABYAGI_DASHBOARD=1 uv run main.py"
echo ""