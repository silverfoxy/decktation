#!/bin/bash
# Installation script for WoW Voice Chat Decky Plugin dependencies

echo "Installing Python dependencies for WoW Voice Chat..."

PLUGIN_DIR="$(dirname "$0")"

# Install dependencies to plugin directory
python3 -m pip install --target="$PLUGIN_DIR" \
    faster-whisper \
    sounddevice \
    numpy \
    pynput

echo "Dependencies installed!"
echo ""
echo "Note: The Whisper model will be downloaded on first use."
echo "Model size: ~150MB for 'base' model"
echo ""
echo "To use a smaller/faster model, edit main.py and change:"
echo "  WhisperModel('base', ...) to WhisperModel('tiny', ...)"
