#!/usr/bin/env bash

# Run script for rexi
# This script activates the virtual environment and runs rexi

# Get the directory where this script is located (resolving symlinks)
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"

# Check if virtual environment exists
if [ ! -d "${VENV_DIR}" ]; then
    echo "Error: Virtual environment not found at ${VENV_DIR}"
    echo "Please run install.sh first"
    exit 1
fi

# Activate virtual environment and run rexi
source "${VENV_DIR}/bin/activate"
python -m rexi.main "$@"
