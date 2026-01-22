#!/bin/bash

# ARC dataset runner wrapper
# Calls the main run.sh script with ARC dataset parameter

cd "$(dirname "$0")/.."
exec ./run.sh --ds arc