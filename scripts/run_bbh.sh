#!/bin/bash

# BBH dataset runner wrapper
# Calls the main run.sh script with BBH dataset parameter

cd "$(dirname "$0")/.."
exec ./run.sh --ds bbh