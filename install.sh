#!/bin/bash

# Rexi Installation Script
# Sets up a virtual environment, installs dependencies, and creates a run script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Rexi...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}Script directory: $SCRIPT_DIR${NC}"

# Set up virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"
echo -e "${GREEN}Creating virtual environment...${NC}"
python3 -m venv "$VENV_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

echo -e "${GREEN}Upgrading pip...${NC}"
python -m pip install --upgrade pip

echo -e "${GREEN}Installing Rexi and dependencies...${NC}"
pip install -e . --break-system-packages

# Create the run script
RUN_SCRIPT="$SCRIPT_DIR/run.sh"
cat > "$RUN_SCRIPT" << EOF
#!/bin/bash

# Rexi Run Script
# Runs Rexi from the virtual environment

set -e

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run Rexi with all passed arguments
python -m rexi.main "\$@"
EOF

# Make the run script executable
chmod +x "$RUN_SCRIPT"

# Create directory ~/.local/bin if it doesn't exist
mkdir -p ~/.local/bin

# Create a symlink to run.sh in ~/.local/bin with full path
SYMLINK_PATH="$HOME/.local/bin/rexi"
FULL_PATH_TO_RUN="$RUN_SCRIPT"

if [ -L "$SYMLINK_PATH" ] || [ -f "$SYMLINK_PATH" ]; then
    echo -e "${YELLOW}Removing existing symlink/file at $SYMLINK_PATH${NC}"
    rm -f "$SYMLINK_PATH"
fi

echo -e "${GREEN}Creating symlink from $SYMLINK_PATH to $FULL_PATH_TO_RUN${NC}"
ln -s "$FULL_PATH_TO_RUN" "$SYMLINK_PATH"

# If the .gitignore doesn't already contain run.sh, add it
if ! grep -q "run.sh" "$SCRIPT_DIR/.gitignore"; then
    echo "run.sh" >> "$SCRIPT_DIR/.gitignore"
    echo -e "${GREEN}Added run.sh to .gitignore${NC}"
fi

echo -e "${GREEN}Installation completed successfully!${NC}"
echo -e "${GREEN}You can now run Rexi using the 'rexi' command from anywhere.${NC}"
echo -e "${GREEN}The application is installed in: $VENV_DIR${NC}"