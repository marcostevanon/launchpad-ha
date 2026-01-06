#!/bin/bash

GREEN='\033[0;32m'
NC='\033[0m'

SERVICE_NAME="com.launchpad.ha"
BASE_DIR="$HOME/.local/launchpad-ha/"
VENV_DIR="$BASE_DIR/venv/"
LAUNCHD_DIR="$HOME/Library/LaunchAgents/"
SERVICE_FILE_PATH="$LAUNCHD_DIR/$SERVICE_NAME.plist"

echo -e "${GREEN}Launchpad HA Controller - macOS Service Installation${NC}"

# Cleanup
echo "Cleaning old install..."
rm -rf "$BASE_DIR"

# Copy project
echo "Installing project..."
mkdir -p "$BASE_DIR"
cp -r ./ "$BASE_DIR"/

# Virtual env
echo "Creating venv..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$BASE_DIR/requirements.txt"
deactivate

# Install plist
echo "Installing LaunchAgent..."
mkdir -p "$LAUNCHD_DIR"
cp packaging/com.launchpad.ha.plist "$SERVICE_FILE_PATH"
chmod 644 "$SERVICE_FILE_PATH"

# Reload service
echo "Reloading LaunchAgent..."
launchctl bootout gui/$(id -u) "$SERVICE_FILE_PATH" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$SERVICE_FILE_PATH"

# 6. # Verify
sleep 2
launchctl print gui/$(id -u)/"$SERVICE_NAME" || true

echo -e "${GREEN}Plist Validation:${NC}"
plutil -lint "$SERVICE_FILE_PATH"

echo -e "${GREEN}Logs:${NC}"
echo "stdout: /tmp/ha-launchpad.out.log"
echo "stderr: /tmp/ha-launchpad.err.log"