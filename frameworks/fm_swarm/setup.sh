#!/bin/bash

set -e

echo "Setting up Swarm framework..."

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
