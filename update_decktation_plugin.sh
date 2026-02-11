#!/bin/bash
# update_decktation_plugin.sh
# Updates the Decktation plugin in the Decky plugins directory

set -e

echo "=== Decktation Plugin Updater ==="
echo ""

# Find plugin directory
if [ -d ~/.local/share/decky/plugins/decktation ]; then
  PLUGIN_DIR=~/.local/share/decky/plugins/decktation
elif [ -d ~/homebrew/plugins/decktation ]; then
  PLUGIN_DIR=~/homebrew/plugins/decktation
else
  echo "Error: Decktation plugin directory not found!"
  echo ""
  echo "Checked locations:"
  echo "  - ~/.local/share/decky/plugins/decktation"
  echo "  - ~/homebrew/plugins/decktation"
  echo ""
  echo "Please install the plugin first or specify the directory:"
  echo "  PLUGIN_DIR=/path/to/plugin $0"
  exit 1
fi

echo "Plugin directory: $PLUGIN_DIR"

# Source directory (where this script is)
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Source directory: $SOURCE_DIR"
echo ""

# Verify we're in the right place
if [ ! -f "$SOURCE_DIR/main.py" ]; then
  echo "Error: main.py not found in $SOURCE_DIR"
  echo "Please run this script from the decktation project directory."
  exit 1
fi

# Copy files (using sudo to handle permission issues)
echo "Copying updated files..."

# Fix ownership first
echo "  → Fixing directory ownership..."
sudo chown -R deck:deck "$PLUGIN_DIR" 2>/dev/null || true

# Core Python files
echo "  → Core Python files..."
sudo cp "$SOURCE_DIR/main.py" "$PLUGIN_DIR/"
sudo cp "$SOURCE_DIR/controller_listener.py" "$PLUGIN_DIR/"
sudo cp "$SOURCE_DIR/wow_voice_chat.py" "$PLUGIN_DIR/"
sudo cp "$SOURCE_DIR/convert_wow_context.py" "$PLUGIN_DIR/"
sudo cp -R "$SOURCE_DIR/lib/" "$PLUGIN_DIR/"

# Built frontend
echo "  → Frontend (dist/index.js)..."
if [ ! -f "$SOURCE_DIR/dist/index.js" ]; then
  echo "Warning: dist/index.js not found. Building now..."
  cd "$SOURCE_DIR"
  npm run build
  cd - >/dev/null
fi
sudo cp "$SOURCE_DIR/dist/index.js" "$PLUGIN_DIR/dist/"

# Setup scripts
echo "  → Setup scripts..."
sudo cp "$SOURCE_DIR/setup_ydotoold.sh" "$PLUGIN_DIR/" 2>/dev/null || true

# Metadata
echo "  → Metadata files..."
sudo cp "$SOURCE_DIR/package.json" "$PLUGIN_DIR/"
[ -f "$SOURCE_DIR/plugin.json" ] && sudo cp "$SOURCE_DIR/plugin.json" "$PLUGIN_DIR/"
[ -f "$SOURCE_DIR/defaults.json" ] && sudo cp "$SOURCE_DIR/defaults.json" "$PLUGIN_DIR/"

# WoW addon (optional)
if [ -d "$SOURCE_DIR/WowAddon" ]; then
  echo "  → WoW addon..."
  sudo mkdir -p "$PLUGIN_DIR/WowAddon"
  sudo cp -r "$SOURCE_DIR/WowAddon/"* "$PLUGIN_DIR/WowAddon/"
fi

# Fix ownership back to deck user
echo "  → Setting correct ownership..."
sudo chown -R deck:deck "$PLUGIN_DIR"

echo "✓ Files copied"
echo ""

# Preserve user config (show status)
echo "User configuration files:"
if [ -f "$PLUGIN_DIR/button_config.json" ]; then
  echo "  ✓ button_config.json exists (preserved)"
  cat "$PLUGIN_DIR/button_config.json"
else
  echo "  ℹ button_config.json not found (will use default L1+R1)"
fi

if [ -f "$PLUGIN_DIR/wow_context.json" ]; then
  echo "  ✓ wow_context.json exists (preserved)"
else
  echo "  ℹ wow_context.json not found (will be created if needed)"
fi
echo ""

# Set permissions
echo "Setting permissions..."
sudo chmod +x "$PLUGIN_DIR/main.py"
sudo chmod +x "$PLUGIN_DIR/controller_listener.py"
sudo chmod +x "$PLUGIN_DIR/setup_ydotoold.sh" 2>/dev/null || true
echo "✓ Permissions set"
echo ""

echo "========================================="
echo "Update completed successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Restart Decky Loader:"
echo "   systemctl --user restart plugin_loader"
echo ""
echo "2. Test the plugin:"
echo "   - Open Quick Access Menu (... button)"
echo "   - Navigate to Decktation"
echo "   - Check for button dropdowns (Button 1, Button 2)"
echo "   - Verify text shows 'Hold L1+R1 to record'"
echo ""
echo "3. Check logs if needed:"
echo "   tail -f /tmp/decktation.log"
