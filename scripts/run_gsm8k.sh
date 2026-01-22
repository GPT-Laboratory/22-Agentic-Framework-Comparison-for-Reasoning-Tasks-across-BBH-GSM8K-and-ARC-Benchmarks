#!/bin/bash

# GSM8K dataset runner wrapper
# Calls the main run.sh script with GSM8K dataset parameter

cd "$(dirname "$0")/.."
exec ./run.sh --ds gsm8k