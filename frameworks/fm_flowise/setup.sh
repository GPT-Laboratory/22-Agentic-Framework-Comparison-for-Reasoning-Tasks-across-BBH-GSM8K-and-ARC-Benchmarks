#!/bin/bash

# Flowise Framework Setup Script
# This script sets up Node.js via volta and installs Flowise locally

set -e

echo "🚀 Setting up Flowise framework..."

# Check if volta is installed
if ! command -v volta &> /dev/null; then
    echo "❌ Volta is not installed. Please install volta first."
    echo "Visit: https://volta.sh/ for installation instructions"
    exit 1
fi

# Pin Node.js v20 for this project (meets >= 18.15.0 requirement)
echo "📦 Pinning Node.js v20 using volta..."
volta pin node@20

# Pin yarn using volta
echo "📦 Pinning yarn using volta..."
volta pin yarn

# Install bun if not already installed
if ! command -v bun &> /dev/null; then
    echo "📦 Installing bun..."
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
fi

# Install Flowise and turndown using bun
echo "📦 Installing Flowise and turndown using bun..."
bun install flowise turndown

# start flowise server in background on port 3010
bunx flowise start --PORT 3010 &

# Setup Python environment with uv
echo "📦 Setting up Python environment..."
uv sync

echo "✅ Flowise framework setup completed!"
echo "📁 You can now run: bunx flowise start --PORT 3010"
echo "🌐 Flowise will be available at: http://localhost:3010"
