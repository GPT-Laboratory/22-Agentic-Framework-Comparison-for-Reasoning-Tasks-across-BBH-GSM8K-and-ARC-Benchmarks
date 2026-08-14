#!/bin/bash

set -e

echo "Setting up SuperAGI framework integration..."

# NOTE: unlike the other frameworks in this repo, 'superagi' is NOT a
# pip-installable library - the "superagi" package on PyPI is an unrelated
# project (pautobot), not TransformerOptimus/SuperAGI. Real SuperAGI is a
# self-hosted stack (FastAPI + Celery + Postgres + Redis + GUI). This script
# only sets up the *client side* (this eval harness). You must separately run
# the actual SuperAGI stack, e.g.:
#
#   git clone https://github.com/TransformerOptimus/SuperAGI.git
#   cd SuperAGI
#   cp config_template.yaml config.yaml   # fill in OPENAI_API_KEY
#   docker compose up --build             # wait for http://localhost:3000
#
# Then in the GUI: Settings -> API Keys -> create a key, and export it:
#   export SUPERAGI_API_KEY=...
#
# Postgres must be reachable from this script for reading back results -
# uncomment the port mapping for `super__postgres` in SuperAGI's
# docker-compose.yaml (adds "5432:5432") or point SUPERAGI_DB_HOST/PORT at
# wherever it's reachable.

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

echo ""
echo "⚠️  Reminder: this only installs the client (requests/psycopg2/datasets)."
echo "   Make sure the actual SuperAGI docker-compose stack is running and"
echo "   SUPERAGI_API_KEY is exported before running main.py."
