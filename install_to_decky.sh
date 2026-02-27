#!/bin/bash
# Fresh installation of Decktation to Decky
set -e

echo "=== Fresh Decktation Installation ==="
echo ""

# Determine plugin directory
if [ -d ~/homebrew/plugins ]; then
    PLUGINS_DIR=~/homebrew/plugins
elif [ -d ~/.local/share/decky/plugins ]; then
    PLUGINS_DIR=~/.local/share/decky/plugins
else
    echo "Error: Cannot find Decky plugins directory!"
    exit 1
fi

PLUGIN_DIR="$PLUGINS_DIR/decktation"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Source: $SOURCE_DIR"
echo "Target: $PLUGIN_DIR"
echo ""

# Remove old installation if exists
if [ -d "$PLUGIN_DIR" ]; then
    echo "Removing old installation..."
    rm -rf "$PLUGIN_DIR"
fi

# Create fresh plugin directory
echo "Creating plugin directory..."
mkdir -p "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR/dist"

# Copy essential files only
echo "Copying files..."
cp "$SOURCE_DIR/main.py" "$PLUGIN_DIR/"
cp "$SOURCE_DIR/controller_listener.py" "$PLUGIN_DIR/"
cp "$SOURCE_DIR/wow_voice_chat.py" "$PLUGIN_DIR/"
cp "$SOURCE_DIR/convert_wow_context.py" "$PLUGIN_DIR/"
cp "$SOURCE_DIR/game_presets.json" "$PLUGIN_DIR/"
cp "$SOURCE_DIR/package.json" "$PLUGIN_DIR/"
cp "$SOURCE_DIR/plugin.json" "$PLUGIN_DIR/"

# Copy built frontend
if [ ! -f "$SOURCE_DIR/dist/index.js" ]; then
    echo "Building frontend..."
    cd "$SOURCE_DIR"
    npm run build
    cd - > /dev/null
fi
cp "$SOURCE_DIR/dist/index.js" "$PLUGIN_DIR/dist/"

# Copy WoW addon if exists
if [ -d "$SOURCE_DIR/WowAddon" ]; then
    echo "Copying WoW addon..."
    cp -r "$SOURCE_DIR/WowAddon" "$PLUGIN_DIR/"
fi

# Copy bundled ydotool binaries if they exist
if [ -d "$SOURCE_DIR/bin" ]; then
    echo "Copying bundled ydotool binaries..."
    cp -r "$SOURCE_DIR/bin" "$PLUGIN_DIR/"
else
    echo "Warning: No bundled ydotool binaries found in bin/"
    echo "Run ./build_ydotool.sh to build them, or they will be downloaded from system"
fi

echo "✓ Files copied"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
echo "This may take a few minutes..."

# Use the venv pip if available, otherwise try to find pip
if [ -f "$SOURCE_DIR/venv/bin/pip" ]; then
    PIP="$SOURCE_DIR/venv/bin/pip"
elif command -v pip3 &> /dev/null; then
    PIP="pip3"
elif command -v pip &> /dev/null; then
    PIP="pip"
else
    echo "Error: pip not found!"
    echo "Creating a temporary venv..."
    python3 -m venv /tmp/decktation_venv
    PIP="/tmp/decktation_venv/bin/pip"
fi

echo "Using pip: $PIP"
echo ""

$PIP install --target "$PLUGIN_DIR/lib" \
    av \
    faster-whisper \
    sounddevice \
    numpy \
    evdev-binary

echo "✓ Dependencies installed"
echo ""

# Set permissions
echo "Setting permissions..."
chmod 644 "$PLUGIN_DIR/main.py"
chmod 644 "$PLUGIN_DIR/wow_voice_chat.py"
chmod 644 "$PLUGIN_DIR/convert_wow_context.py"
chmod 755 "$PLUGIN_DIR/controller_listener.py"

echo "✓ Permissions set"
echo ""

# Verify installation
echo "Verifying installation..."
if [ -d "$PLUGIN_DIR/lib/av" ]; then
    echo "✓ av module installed"
else
    echo "✗ av module missing!"
fi

if [ -d "$PLUGIN_DIR/lib/faster_whisper" ]; then
    echo "✓ faster-whisper installed"
else
    echo "✗ faster-whisper missing!"
fi

if [ -f "$PLUGIN_DIR/dist/index.js" ]; then
    echo "✓ Frontend built"
else
    echo "✗ Frontend missing!"
fi

echo ""
echo "========================================="
echo "Installation complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Restart Decky Loader:"
echo "   systemctl --user restart plugin_loader"
echo ""
echo "2. Wait ~10 seconds for Decky to start"
echo ""
echo "3. Check logs:"
echo "   tail -f /tmp/decktation.log"
echo ""
echo "4. Open Quick Access Menu (... button)"
echo "   Navigate to Decktation plugin"
echo ""
echo "You should see button configuration dropdowns!"
echo ""
