#!/bin/bash

set -e

echo "Setting up Upsonic framework..."

# Read Python version from .python-version file
if [ -f ".python-version" ]; then
    PYTHON_VERSION=$(cat .python-version | tr -d '\n\r')
    echo "📍 Using Python version from .python-version: $PYTHON_VERSION"
else
    echo "❌ .python-version file not found"
    exit 1
fi

# Setup Python environment with uv
echo "📦 Setting up Python environment..."
uv sync

echo "✅ Upsonic framework setup completed successfully!"
echo "💡 Run 'uv run main.py' to test with first 3 tasks"
echo "💡 Run 'uv run main.py --full' to run all BBH tasks"