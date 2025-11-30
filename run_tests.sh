#!/bin/bash

# Rexi Test Runner Script
# Runs unit tests using the project's virtual environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located (resolving symlinks)
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

echo -e "${GREEN}Running Rexi unit tests...${NC}"
echo -e "${YELLOW}Project directory: $SCRIPT_DIR${NC}"

# Activate the virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
    echo -e "${RED}Please run install.sh first to set up the environment.${NC}"
    exit 1
fi

source "$VENV_DIR/bin/activate"

echo -e "${GREEN}Virtual environment activated.${NC}"

# Check if we have arguments to pass to unittest
if [ $# -eq 0 ]; then
    # Run all tests with verbose output
    echo -e "${GREEN}Running all unit tests...${NC}"
    python -m unittest discover tests/ -v
else
    # Run specific test as provided by arguments
    echo -e "${GREEN}Running specified tests: $@${NC}"
    python -m unittest "$@"
fi

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed!${NC}"
fi

exit $EXIT_CODE