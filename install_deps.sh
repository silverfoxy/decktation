#!/bin/bash
# Installation script for Decktation Plugin dependencies
# This bundles dependencies into the lib/ folder for distribution

echo "Installing dependencies for Decktation..."

PLUGIN_DIR="$(dirname "$0")"
LIB_DIR="$PLUGIN_DIR/lib"

# Remove old lib directory if it exists
if [ -d "$LIB_DIR" ]; then
    echo "Removing old lib directory..."
    rm -rf "$LIB_DIR"
fi

# Install Python dependencies to lib folder
echo "Installing Python dependencies to lib/..."
# Use venv pip to install packages
"$PLUGIN_DIR/venv/bin/pip" install --target "$LIB_DIR" faster-whisper sounddevice numpy evdev-binary

echo ""
echo "Installation complete!"
echo ""
echo "Dependencies bundled in lib/:"
echo "  - faster-whisper (Whisper speech recognition)"
echo "  - sounddevice (audio recording)"
echo "  - numpy (audio processing)"
echo ""
echo "Note: xdotool is used for keyboard input (pre-installed on Steam Deck)"
echo ""
