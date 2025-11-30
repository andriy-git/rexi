#!/bin/bash

# Rexi Run Script
# Runs Rexi from the virtual environment

set -e

# Get the directory where this script file is located (resolving symlinks)
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run Rexi with all passed arguments
python -m rexi.main "$@"
