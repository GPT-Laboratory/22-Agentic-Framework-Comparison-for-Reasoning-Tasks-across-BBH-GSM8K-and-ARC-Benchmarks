#!/bin/bash
set -e

echo "🤖 Setting up ANUS framework..."

echo "📦 Installing client dependencies..."
if ! uv sync; then
    echo "❌ ERROR: Failed to install dependencies"
    exit 1
fi
echo "✅ Client dependencies installed"

echo "🔑 Validating OpenAI API access (used by both ANUS itself and utils.py extraction)..."
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

echo "🔍 Checking for the real ANUS CLI (npm package @anus-dev/anus)..."
if ! command -v anus &> /dev/null; then
    echo "⚠️  'anus' not found on PATH."
    if ! command -v npm &> /dev/null; then
        echo "❌ ERROR: npm is not installed. Install Node.js (v20+) first: https://nodejs.org"
        exit 1
    fi
    echo "📦 Installing @anus-dev/anus globally via npm..."
    if ! npm install -g @anus-dev/anus; then
        echo "❌ ERROR: Failed to install @anus-dev/anus"
        exit 1
    fi
fi

if command -v anus &> /dev/null; then
    echo "✅ ANUS CLI found: $(command -v anus)"
else
    echo "❌ ERROR: ANUS CLI still not found on PATH after install attempt"
    exit 1
fi

echo "🔧 Patching ANUS's bundled max_tokens -> max_completion_tokens for gpt-5.x/o1/o3/o4 models..."
echo "   (This lives in an npm-installed file and must be reapplied after any reinstall/update -"
echo "   that's why this patch step runs automatically every time setup.sh runs.)"
ANUS_BUNDLE_PATH=$(dirname "$(dirname "$(readlink -f "$(command -v anus)" 2>/dev/null || command -v anus)")")/lib/node_modules/@anus-dev/anus/bundle/anus.js
if [ ! -f "$ANUS_BUNDLE_PATH" ]; then
    # Fallback: try common global npm prefix locations
    for candidate in "/opt/homebrew/lib/node_modules/@anus-dev/anus/bundle/anus.js" "/usr/local/lib/node_modules/@anus-dev/anus/bundle/anus.js"; do
        if [ -f "$candidate" ]; then
            ANUS_BUNDLE_PATH="$candidate"
            break
        fi
    done
fi

if [ -f "$ANUS_BUNDLE_PATH" ]; then
    python3 - "$ANUS_BUNDLE_PATH" <<'PYEOF'
import re, sys

path = sys.argv[1]
with open(path) as f:
    content = f.read()

old = "temperature: genConfig?.temperature ?? 0.7"  # unchanged - already correctly 0 in real usage
old_pattern = r"max_tokens:\s*genConfig\?\.maxOutputTokens\s*\?\?\s*4e3"
new_snippet = (
    '[((this.model ?? request.model ?? "").startsWith("gpt-5") || '
    '(this.model ?? request.model ?? "").startsWith("o1") || '
    '(this.model ?? request.model ?? "").startsWith("o3") || '
    '(this.model ?? request.model ?? "").startsWith("o4")) '
    '? "max_completion_tokens" : "max_tokens"]: genConfig?.maxOutputTokens ?? 4e3'
)

changed = False
if "max_completion_tokens" in content:
    print("✅ max_tokens param-name patch already applied")
else:
    content, count = re.subn(old_pattern, new_snippet, content)
    print(f"✅ Patched max_tokens param name in {count} occurrence(s)")
    changed = True

old_gcc = """      generateContentConfig = {
        temperature: 0,
        topP: 1
      };"""
new_gcc = """      generateContentConfig = {
        temperature: 0,
        topP: 1,
        maxOutputTokens: 1200
      };"""
if "maxOutputTokens: 1200" in content:
    print("✅ maxOutputTokens:1200 patch already applied")
elif old_gcc in content:
    content = content.replace(old_gcc, new_gcc)
    print("✅ Patched default maxOutputTokens to 1200")
    changed = True
else:
    print("⚠️  Could not find the generateContentConfig block to patch maxOutputTokens - check manually.")

if changed:
    with open(path, "w") as f:
        f.write(content)
PYEOF
else
    echo "⚠️  Could not locate anus.js bundle to patch automatically."
    echo "   Find it with: npm list -g @anus-dev/anus --parseable"
    echo "   Then patch manually if you hit a 'max_tokens' error, or want to enforce a 1200-token cap."
fi

echo "🔧 Disabling ANUS's built-in tools (shell/file access) via ~/.anus/settings.json..."
echo "   (Pure text-reasoning benchmark questions never need these tools; leaving"
echo "   them enabled was causing the model to spam pointless no-op tool calls"
echo "   instead of answering directly.)"
mkdir -p ~/.anus
if [ -f ~/.anus/settings.json ]; then
    if grep -q '"coreTools"' ~/.anus/settings.json; then
        echo "✅ ~/.anus/settings.json already configures coreTools, leaving as-is"
    else
        echo "⚠️  ~/.anus/settings.json exists but doesn't set coreTools - not overwriting it."
        echo "   Add \"coreTools\": [] to it manually if you see tool-call spam in results."
    fi
else
    cat > ~/.anus/settings.json << 'ANUSSETTINGSEOF'
{
  "coreTools": []
}
ANUSSETTINGSEOF
    echo "✅ Created ~/.anus/settings.json with coreTools disabled"
fi

echo "📁 Creating outputs directory..."
mkdir -p outputs
echo "✅ Outputs directory ready"

echo ""
echo "🎉 ANUS framework setup complete!"
echo ""
echo "Ready to run:"
echo "  uv run main.py          # Sample mode"
echo "  uv run main.py --full   # Full benchmarking"
echo "  uv run main.py --continue"
echo ""
echo "Note: ANUS is redirected from its default xAI/Grok backend to real"
echo "OpenAI via GROK_BASE_URL/GROK_API_KEY/GROK_MODEL, set automatically"
echo "by main.py from your existing OPENAI_API_KEY - no separate xAI key"
echo "needed."
echo ""