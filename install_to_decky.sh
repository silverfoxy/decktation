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

# Native wheels must run in the matching packaged interpreter, never Decky's
# or the system Python. Refuse incomplete source-only installs before changes.
if [ ! -x "$SOURCE_DIR/bin/runtime/bin/python3.11" ] || [ ! -d "$SOURCE_DIR/bin/python/numpy" ]; then
    echo "Error: the built private Python runtime is missing. Install the complete plugin ZIP or build the backend artifact first."
    exit 1
fi

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
mkdir -p "$PLUGIN_DIR/bin"

# Copy essential files only
echo "Copying files..."
cp "$SOURCE_DIR/main.py" "$PLUGIN_DIR/"
cp "$SOURCE_DIR/backend/src/decktation_backend.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/runtime_proxy.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/runtime_worker.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/plugin_update.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/audio_runtime.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/controller_listener.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/controller_debug_report.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/controller_debug_session.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/binding_capture.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/deck_hid.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/telemetry.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/wow_voice_chat.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/resident_whisper.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/clipboard_injection.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/convert_wow_context.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/gamepad_evdev.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/haptic_feedback.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/recording_overlay.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/recording_overlay_manager.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/overlay_render.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/backend/src/review_gesture.py" "$PLUGIN_DIR/bin/"
cp "$SOURCE_DIR/defaults/game_presets.json" "$PLUGIN_DIR/"
cp "$SOURCE_DIR/defaults/channel_languages.json" "$PLUGIN_DIR/"
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

# Dependencies and their matching interpreter came from the built bin/ tree.
echo "✓ Private Python runtime and dependencies copied"
echo ""

# Set permissions
echo "Setting permissions..."
chmod 644 "$PLUGIN_DIR/main.py"
chmod 644 "$PLUGIN_DIR/bin/decktation_backend.py"
chmod 644 "$PLUGIN_DIR/bin/audio_runtime.py"
chmod 644 "$PLUGIN_DIR/bin/deck_hid.py"
chmod 644 "$PLUGIN_DIR/bin/telemetry.py"
chmod 644 "$PLUGIN_DIR/bin/wow_voice_chat.py"
chmod 644 "$PLUGIN_DIR/bin/resident_whisper.py"
chmod 644 "$PLUGIN_DIR/bin/convert_wow_context.py"
chmod 755 "$PLUGIN_DIR/bin/controller_listener.py"
[ ! -f "$PLUGIN_DIR/bin/whisper-server" ] || chmod 755 "$PLUGIN_DIR/bin/whisper-server"

echo "✓ Permissions set"
echo ""

# Verify installation
echo "Verifying installation..."
if [ -d "$PLUGIN_DIR/bin/python/numpy" ]; then
    echo "✓ numpy installed"
else
    echo "✗ numpy missing!"
fi

if [ -x "$PLUGIN_DIR/bin/whisper-server" ]; then
    echo "✓ whisper.cpp server installed"
else
    echo "✗ whisper-server missing; install from a built Decktation package"
fi

if [ -d "$PLUGIN_DIR/lib/sentry_sdk" ]; then
    echo "✓ sentry-sdk installed"
else
    echo "✗ sentry-sdk missing!"
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
echo "   tail -f /home/deck/homebrew/logs/decktation/*.log"
echo ""
echo "4. Open Quick Access Menu (... button)"
echo "   Navigate to Decktation plugin"
echo ""
echo "You should see button configuration dropdowns!"
echo ""
